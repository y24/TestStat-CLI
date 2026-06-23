import json
import os
import urllib.error
import urllib.request
from datetime import datetime


RESULT_KEY_MAP = {
    "Pass": "Pass",
    "Fixed": "Fixed",
    "Fail": "Fail",
    "Blocked": "Blocked",
    "Suspend": "Suspend",
    "N/A": "N/A",
}


def _file_name(path):
    return os.path.basename(path.replace("\\", "/"))


def _first_error_message(error):
    if isinstance(error, dict):
        return error.get("message") or error.get("type") or json.dumps(error, ensure_ascii=False)
    return str(error)


def _build_results(total):
    return {api_key: int(total.get(source_key, 0) or 0) for source_key, api_key in RESULT_KEY_MAP.items()}


def _build_daily_rows(daily_data):
    rows = []
    for date, counts in sorted((daily_data or {}).items()):
        rows.append({
            "date": date,
            "Pass": int(counts.get("Pass", 0) or 0),
            "Fixed": int(counts.get("Fixed", 0) or 0),
            "Fail": int(counts.get("Fail", 0) or 0),
            "Blocked": int(counts.get("Blocked", 0) or 0),
            "Suspend": int(counts.get("Suspend", 0) or 0),
            "N/A": int(counts.get("N/A", 0) or 0),
            "completed": int(counts.get("完了数", 0) or 0),
            "executed": int(counts.get("消化数", 0) or 0),
            "planned": counts.get("計画数"),
        })
    return rows


def _build_person_rows(by_name):
    rows = []
    for date, people in sorted((by_name or {}).items()):
        for person, count in sorted((people or {}).items()):
            if person:
                rows.append({
                    "date": date,
                    "person": person,
                    "count": int(count or 0),
                })
    return rows


def build_progress_payload(project_info, results, sender=None):
    files = []
    for filepath, result in results:
        if not isinstance(result, dict):
            continue

        label = result.get("label", "")
        environments = result.get("target_environments", [])
        environment = ", ".join(environments) if environments else None

        if "error" in result:
            file_payload = {
                "file_name": _file_name(filepath),
                "label": label,
                "environment": environment,
                "total_cases": 0,
                "available_cases": 0,
                "excluded_cases": 0,
                "completed": 0,
                "executed": 0,
                "not_run": 0,
                "completed_rate": 0,
                "executed_rate": 0,
                "results": _build_results({}),
                "daily": [],
                "by_person": [],
                "error": _first_error_message(result["error"]),
            }
            if result.get("source_url"):
                file_payload["source_url"] = result["source_url"]
            files.append(file_payload)
            continue

        stats = result.get("stats", {})
        total = result.get("total", {})
        run = result.get("run", {})
        available = int(stats.get("available", 0) or 0)
        completed = int(total.get("完了数", stats.get("completed", 0)) or 0)
        executed = int(total.get("消化数", stats.get("executed", 0)) or 0)

        file_payload = {
            "file_name": _file_name(filepath),
            "label": label,
            "environment": environment,
            "total_cases": int(stats.get("all", 0) or 0),
            "available_cases": available,
            "excluded_cases": int(stats.get("excluded", 0) or 0),
            "completed": completed,
            "executed": executed,
            "not_run": int(total.get("未実施", stats.get("incompleted", 0)) or 0),
            "completed_rate": round((completed / available * 100), 2) if available > 0 else 0,
            "executed_rate": round((executed / available * 100), 2) if available > 0 else 0,
            "start_date": run.get("start_date"),
            "latest_update": run.get("last_update"),
            "results": _build_results(total),
            "daily": _build_daily_rows(result.get("daily", {})),
            "by_person": _build_person_rows(result.get("by_name", {})),
        }
        if result.get("source_url"):
            file_payload["source_url"] = result["source_url"]
        files.append(file_payload)

    return {
        "testing_id": project_info["testing_id"],
        "project_name": project_info["project_name"],
        "sender": sender,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "files": files,
    }


def _get_project_status(base_url, testing_id, timeout=10):
    url = f"{base_url.rstrip('/')}/v1/projects/{testing_id}"
    req = urllib.request.Request(url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            if 200 <= response.status < 300:
                return True, json.loads(body)
            return False, f"プロジェクト状態の確認に失敗しました: ステータスコード {response.status}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, None
        body = e.read().decode("utf-8", errors="replace")
        return False, f"プロジェクト状態の確認に失敗しました: ステータスコード {e.code}, レスポンス: {body}"
    except urllib.error.URLError as e:
        return False, f"プロジェクト状態の確認に失敗しました: {e}"
    except Exception as e:
        return False, f"プロジェクト状態の確認に失敗しました: {e}"


def send_progress(base_url, payload, timeout=10, logger=None):
    if not base_url:
        return False, "reporting_api.base_url が設定されていません。"

    testing_id = payload.get("testing_id")
    if testing_id is not None:
        ok, project = _get_project_status(base_url, testing_id, timeout=timeout)
        if not ok:
            return False, project
        if project and project.get("archived"):
            return False, f"testing_id={testing_id} はアーカイブ済みのため進捗データを送信しません。"

    url = f"{base_url.rstrip('/')}/v1/progress"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            if 200 <= response.status < 300:
                if logger:
                    logger.log(f"進捗データを送信しました: {body}")
                return True, body
            return False, f"APIエラー: ステータスコード {response.status}, レスポンス: {body}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"APIエラー: ステータスコード {e.code}, レスポンス: {body}"
    except urllib.error.URLError as e:
        return False, f"APIへの接続に失敗しました: {e}"
    except Exception as e:
        return False, f"進捗データの送信に失敗しました: {e}"
