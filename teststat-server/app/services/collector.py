from __future__ import annotations

import ctypes
import json
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.plan import PlanLabel
from app.models.project import Project
from app.schemas.collect import CollectFailure, CollectResult

_LAST_RESULT: CollectResult | None = None


@dataclass(frozen=True)
class CollectTarget:
    testing_id: int
    project_name: str
    files: tuple[tuple[str, str], ...]


def get_last_result() -> CollectResult | None:
    return _LAST_RESULT


def set_last_result(result: CollectResult) -> None:
    global _LAST_RESULT
    _LAST_RESULT = result


def count_collect_targets(db: Session, testing_id: int | None = None) -> int:
    query = (
        select(func.count(func.distinct(PlanLabel.testing_id)))
        .join(Project, Project.testing_id == PlanLabel.testing_id)
        .where(Project.archived.is_(False), PlanLabel.source_url.is_not(None), PlanLabel.source_url != "")
    )
    if testing_id is not None:
        query = query.where(PlanLabel.testing_id == testing_id)
    return int(db.scalar(query) or 0)


def collect_all(db: Session | None = None, *, settings: Settings | None = None) -> CollectResult:
    return _collect(db, settings=settings, testing_id=None)


def collect_project(db: Session | None = None, testing_id: int | None = None, *, settings: Settings | None = None) -> CollectResult:
    if testing_id is None:
        raise ValueError("testing_id is required")
    return _collect(db, settings=settings, testing_id=testing_id)


def collect_all_with_new_session() -> CollectResult:
    with SessionLocal() as db:
        return collect_all(db, settings=get_settings())


def collect_project_with_new_session(testing_id: int) -> CollectResult:
    with SessionLocal() as db:
        return collect_project(db, testing_id, settings=get_settings())


def _collect(db: Session | None, *, settings: Settings | None, testing_id: int | None) -> CollectResult:
    settings = settings or get_settings()
    own_session = db is None
    session = db or SessionLocal()
    started_at = datetime.now()
    result = CollectResult(targets=0, succeeded=[], failed=[], auth_error=False, started_at=started_at)

    try:
        if not settings.collect_enabled:
            result.failed.append(CollectFailure(testing_id=testing_id or 0, reason="other", message="collector disabled"))
            return _finish(result)
        targets = _load_targets(session, testing_id=testing_id)
        result.targets = len(targets)
        if not targets:
            return _finish(result)
        if not settings.tstat_command.strip():
            for target in targets:
                result.failed.append(CollectFailure(
                    testing_id=target.testing_id,
                    reason="other",
                    message="TSTAT_COMMAND is not configured",
                ))
            return _finish(result)

        _ensure_log_dir(settings)
        base_work_dir = Path(settings.collect_work_dir) if settings.collect_work_dir.strip() else None
        with tempfile.TemporaryDirectory(prefix="teststat_collect_", dir=str(base_work_dir) if base_work_dir else None) as tmp:
            for target in targets:
                yaml_path = Path(tmp) / f"collect_{target.testing_id}.yaml"
                yaml_path.write_text(build_list_yaml(target), encoding="utf-8", newline="\n")
                try:
                    completed = _run_tstat(settings, yaml_path)
                except subprocess.TimeoutExpired as exc:
                    completed = subprocess.CompletedProcess(
                        args=exc.cmd,
                        returncode=124,
                        stdout=exc.stdout or "",
                        stderr=(exc.stderr or "") + f"\ntstat timed out after {settings.collect_timeout_sec} seconds",
                    )
                if completed.returncode == 0:
                    result.succeeded.append(target.testing_id)
                else:
                    failure = _classify_failure(target.testing_id, completed)
                    if failure.reason == "auth":
                        result.auth_error = True
                    result.failed.append(failure)
                _write_log(settings, target, yaml_path, completed)
        return _finish(result)
    finally:
        if own_session:
            session.close()


def _finish(result: CollectResult) -> CollectResult:
    result.finished_at = datetime.now()
    set_last_result(result)
    return result


def _load_targets(db: Session, testing_id: int | None = None) -> list[CollectTarget]:
    query = (
        select(Project.testing_id, Project.name, PlanLabel.label, PlanLabel.source_url)
        .join(PlanLabel, PlanLabel.testing_id == Project.testing_id)
        .where(Project.archived.is_(False), PlanLabel.source_url.is_not(None), PlanLabel.source_url != "")
        .order_by(Project.testing_id, PlanLabel.label)
    )
    if testing_id is not None:
        query = query.where(Project.testing_id == testing_id)

    grouped: dict[int, tuple[str, list[tuple[str, str]]]] = {}
    for row_testing_id, project_name, label, source_url in db.execute(query):
        if not source_url:
            continue
        name, files = grouped.setdefault(row_testing_id, (project_name, []))
        files.append((label, source_url))

    return [
        CollectTarget(testing_id=tid, project_name=name, files=tuple(files))
        for tid, (name, files) in grouped.items()
    ]


def build_list_yaml(target: CollectTarget) -> str:
    lines = [
        "project:",
        f"  project_name: {_yaml_scalar(target.project_name)}",
        f"  testing_id: {target.testing_id}",
        "  files:",
    ]
    for label, source_url in target.files:
        lines.append(f"    - label: {_yaml_scalar(label)}")
        lines.append(f"      path: {_yaml_scalar(source_url)}")
    return "\n".join(lines) + "\n"


def _yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _run_tstat(settings: Settings, yaml_path: Path) -> subprocess.CompletedProcess[str]:
    command = split_command(settings.tstat_command)
    args = [*command, "-l", str(yaml_path), "--json"]
    if settings.tstat_config.strip():
        args.extend(["--config", settings.tstat_config.strip()])
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=settings.collect_timeout_sec,
        shell=False,
    )


def split_command(command: str) -> list[str]:
    if os.name != "nt":
        return shlex.split(command)

    ctypes.windll.shell32.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    ctypes.windll.shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    argc = ctypes.c_int()
    argv = ctypes.windll.shell32.CommandLineToArgvW(command, ctypes.byref(argc))
    if not argv:
        raise ValueError("failed to parse TSTAT_COMMAND")
    try:
        return [argv[i] for i in range(argc.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


def _classify_failure(testing_id: int, completed: subprocess.CompletedProcess[str]) -> CollectFailure:
    message = _extract_error_message(completed)
    lowered = message.lower()
    auth_markers = ("az login", "azure にログイン", "401", "403", "unauthorized", "forbidden", "access token")
    if any(marker in lowered for marker in auth_markers) or "アクセス権" in message:
        return CollectFailure(testing_id=testing_id, reason="auth", message=message)
    if "download" in lowered or "sharepoint" in lowered or "graph" in lowered:
        return CollectFailure(testing_id=testing_id, reason="download", message=message)
    if "reporting_api" in lowered or "progress" in lowered or "送信" in message:
        return CollectFailure(testing_id=testing_id, reason="report", message=message)
    if "処理" in message or "aggregate" in lowered:
        return CollectFailure(testing_id=testing_id, reason="aggregate", message=message)
    return CollectFailure(testing_id=testing_id, reason="other", message=message)


def _extract_error_message(completed: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
    if not text:
        return f"tstat exited with code {completed.returncode}"
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        messages = list(_collect_messages(data))
        if messages:
            return " / ".join(messages)
    return text[-4000:]


def _collect_messages(value) -> Iterable[str]:
    if isinstance(value, dict):
        for key in ("error", "warnings", "reporting_api", "message", "details"):
            if key in value:
                yield from _collect_messages(value[key])
        return
    if isinstance(value, list):
        for item in value:
            yield from _collect_messages(item)
        return
    if isinstance(value, str) and value.strip():
        yield value.strip()


def _ensure_log_dir(settings: Settings) -> None:
    Path(settings.collect_log_dir).mkdir(parents=True, exist_ok=True)


def _write_log(settings: Settings, target: CollectTarget, yaml_path: Path, completed: subprocess.CompletedProcess[str]) -> None:
    log_dir = Path(settings.collect_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    log_path = log_dir / f"collect_{stamp}.log"
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] testing_id={target.testing_id} yaml={yaml_path}\n")
        f.write(f"exit_code={completed.returncode}\n")
        if completed.stdout:
            f.write("--- stdout ---\n")
            f.write(completed.stdout)
            f.write("\n")
        if completed.stderr:
            f.write("--- stderr ---\n")
            f.write(completed.stderr)
            f.write("\n")





