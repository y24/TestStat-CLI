from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud.bug import build_work_item_url, delete_bug_count_data, get_open_bugs, replace_bugs
from app.crud.project import get_project
from app.database import get_db
from app.schemas.bug import BugSyncResponse, OpenBugItem
from app.services.azure_devops import (
    AzureDevOpsAuthError,
    AzureDevOpsError,
    AzureDevOpsNotConfigured,
    WorkItemNotFound,
    fetch_child_bugs,
)

router = APIRouter(prefix="/api/v1", tags=["bugs"])


@router.post("/projects/{testing_id}/bugs/sync", response_model=BugSyncResponse)
def sync_bugs(testing_id: int, db: Session = Depends(get_db)) -> BugSyncResponse:
    # プロジェクト存在確認（無ければ 404）。
    get_project(db, testing_id)

    try:
        bugs = fetch_child_bugs(testing_id)
    except WorkItemNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="親 Work Item が見つかりません",
        )
    except AzureDevOpsNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure DevOps 連携が設定されていません",
        )
    except AzureDevOpsAuthError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Azure DevOps の認証に失敗しました",
        )
    except AzureDevOpsError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Azure DevOps への接続に失敗しました",
        )

    suspend_states = get_settings().azure_devops_bug_suspend_status_set
    try:
        return replace_bugs(
            db, testing_id, bugs, suspend_states, datetime.now(timezone.utc).replace(tzinfo=None)
        )
    except Exception:
        db.rollback()
        raise


@router.delete("/projects/{testing_id}/bugs", status_code=status.HTTP_204_NO_CONTENT)
def delete_bugs(testing_id: int, db: Session = Depends(get_db)) -> None:
    # プロジェクト存在確認（無ければ 404）。
    get_project(db, testing_id)
    try:
        delete_bug_count_data(db, testing_id)
    except Exception:
        db.rollback()
        raise


@router.get("/projects/{testing_id}/bugs/open", response_model=list[OpenBugItem])
def list_open_bugs(testing_id: int, db: Session = Depends(get_db)) -> list[OpenBugItem]:
    project = get_project(db, testing_id)
    settings = get_settings()
    if project.bug_count_source == "test_result":
        try:
            bugs = fetch_child_bugs(testing_id, settings)
        except WorkItemNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="親 Work Item が見つかりません",
            )
        except AzureDevOpsNotConfigured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Azure DevOps 連携が設定されていません",
            )
        except AzureDevOpsAuthError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Azure DevOps の認証に失敗しました",
            )
        except AzureDevOpsError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Azure DevOps への接続に失敗しました",
            )
        return [
            OpenBugItem(
                work_item_id=bug.work_item_id,
                title=bug.title or None,
                state=bug.state or None,
                url=build_work_item_url(bug.work_item_id, settings),
                is_suspended=bug.state in settings.azure_devops_bug_suspend_status_set,
            )
            for bug in bugs
            if bug.finish_date is None or bug.state in settings.azure_devops_bug_suspend_status_set
        ]
    return get_open_bugs(db, testing_id, settings, settings.azure_devops_bug_suspend_status_set)
