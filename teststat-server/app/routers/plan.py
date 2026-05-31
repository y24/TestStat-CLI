from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.crud.pb_chart import get_pb_chart
from app.crud.plan import activate_plan, create_plan, delete_plan, get_plan_detail, list_plans
from app.database import get_db
from app.schemas.pb_chart import PbChartResponse
from app.schemas.plan import PlanCreate, PlanDetail, PlanItem

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.get("/projects/{testing_id}/plans", response_model=list[PlanItem])
def read_plans(testing_id: int, db: Session = Depends(get_db)) -> list[PlanItem]:
    return list_plans(db, testing_id)


@router.post(
    "/projects/{testing_id}/plans",
    response_model=PlanDetail,
    status_code=status.HTTP_201_CREATED,
)
def post_plan(testing_id: int, payload: PlanCreate, db: Session = Depends(get_db)) -> PlanDetail:
    return create_plan(db, testing_id, payload)


@router.get("/plans/{plan_id}", response_model=PlanDetail)
def read_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanDetail:
    return get_plan_detail(db, plan_id)


@router.post("/plans/{plan_id}/activate", response_model=PlanItem)
def post_activate(plan_id: int, db: Session = Depends(get_db)) -> PlanItem:
    return activate_plan(db, plan_id)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_route(plan_id: int, db: Session = Depends(get_db)) -> None:
    delete_plan(db, plan_id)


@router.get("/projects/{testing_id}/pb-chart", response_model=PbChartResponse)
def read_pb_chart(
    testing_id: int,
    label: str | None = Query(default=None, description="テスト(label)で絞り込む。未指定=全テスト合算"),
    include_past_plans: bool = Query(default=False, description="過去の計画バージョンも返す"),
    db: Session = Depends(get_db),
) -> PbChartResponse:
    return get_pb_chart(db, testing_id, label=label, include_past_plans=include_past_plans)
