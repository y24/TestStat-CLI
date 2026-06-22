from __future__ import annotations

from app.services.collector import collect_all_with_new_session


def main() -> int:
    result = collect_all_with_new_session()
    print(result.model_dump_json(indent=2))
    if result.auth_error:
        return 2
    if result.targets > 0 and not result.succeeded and result.failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
