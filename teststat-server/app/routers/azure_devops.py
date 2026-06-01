from dataclasses import asdict

from fastapi import APIRouter, HTTPException, status

from app.schemas.azure_devops import WorkItemResponse
from app.services.azure_devops import (
    AzureDevOpsAuthError,
    AzureDevOpsError,
    AzureDevOpsNotConfigured,
    WorkItemNotFound,
    fetch_work_item,
)

router = APIRouter(prefix="/api/v1/azure-devops", tags=["azure-devops"])


@router.get("/work-items/{work_item_id}", response_model=WorkItemResponse)
def read_work_item(work_item_id: int) -> WorkItemResponse:
    try:
        info = fetch_work_item(work_item_id)
    except WorkItemNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work Item が見つかりません",
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
    return WorkItemResponse(**asdict(info))
