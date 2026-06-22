from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.progress import get_daily_progress, get_file_progress, get_progress_summary, list_testings, replace_progress
from app.database import get_db
from app.schemas.progress import DailyProgressItem, FileProgressItem, ProgressPostResponse, ProgressRequest, ProgressSummaryResponse, TestingItem

router = APIRouter(prefix="/api/v1", tags=["progress"])


@router.post("/progress", response_model=ProgressPostResponse)
def post_progress(payload: ProgressRequest, db: Session = Depends(get_db)) -> ProgressPostResponse:
    try:
        return replace_progress(db, payload)
    except Exception:
        db.rollback()
        raise


@router.get("/progress/{testing_id}", response_model=ProgressSummaryResponse)
def read_progress_summary(testing_id: int, db: Session = Depends(get_db)) -> ProgressSummaryResponse:
    summary = get_progress_summary(db, testing_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Testing ID not found")
    return summary


@router.get("/progress/{testing_id}/files", response_model=list[FileProgressItem])
def read_progress_files(testing_id: int, db: Session = Depends(get_db)) -> list[FileProgressItem]:
    # コレクション系は未開始（Testing 行なし）でも 200 + 空配列を返す。空集合は Not Found ではない。
    return get_file_progress(db, testing_id)


@router.get("/progress/{testing_id}/daily", response_model=list[DailyProgressItem])
def read_progress_daily(testing_id: int, db: Session = Depends(get_db)) -> list[DailyProgressItem]:
    # コレクション系は未開始（Testing 行なし）でも 200 + 空配列を返す。空集合は Not Found ではない。
    return get_daily_progress(db, testing_id)


@router.get("/testings", response_model=list[TestingItem])
def read_testings(db: Session = Depends(get_db)) -> list[TestingItem]:
    return list_testings(db)
