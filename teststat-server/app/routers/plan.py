from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud.pb_chart import get_pb_chart
from app.crud.plan import (
    activate_plan,
    create_plan,
    create_plan_label,
    delete_plan,
    delete_plan_label,
    delete_project_label,
    get_plan_detail,
    list_plan_labels,
    list_plans,
    update_plan_label,
    update_plan_label_order,
    update_project_label,
)
from app.database import get_db
from app.schemas.pb_chart import PbChartResponse
from app.schemas.plan import PlanCreate, PlanDetail, PlanItem, PlanLabelCreate, PlanLabelItem, PlanLabelOrderUpdate, PlanLabelUpdate, ProjectLabelUpdate
from app.services.collector import build_project_list_yaml

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.get("/projects/{testing_id}/plans", response_model=list[PlanItem])
def read_plans(testing_id: int, db: Session = Depends(get_db)) -> list[PlanItem]:
    return list_plans(db, testing_id)


@router.get("/projects/{testing_id}/plan-labels", response_model=list[PlanLabelItem])
def read_plan_labels(testing_id: int, db: Session = Depends(get_db)) -> list[PlanLabelItem]:
    return list_plan_labels(db, testing_id)


@router.get("/projects/{testing_id}/list-yaml")
def download_project_list_yaml(testing_id: int, db: Session = Depends(get_db)) -> Response:
    yaml_text = build_project_list_yaml(db, testing_id)
    if yaml_text is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="downloadable list yaml not found")
    filename = f"teststat_{testing_id}_list.yaml"
    return Response(
        content=yaml_text,
        media_type="application/x-yaml; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )

@router.post(
    "/projects/{testing_id}/plan-labels",
    response_model=PlanLabelItem,
    status_code=status.HTTP_201_CREATED,
)
def post_plan_label(
    testing_id: int,
    payload: PlanLabelCreate,
    db: Session = Depends(get_db),
) -> PlanLabelItem:
    return create_plan_label(db, testing_id, payload)


@router.patch("/projects/{testing_id}/labels", response_model=PlanLabelItem)
def patch_project_label(
    testing_id: int,
    payload: ProjectLabelUpdate,
    db: Session = Depends(get_db),
) -> PlanLabelItem:
    return update_project_label(db, testing_id, payload)


@router.patch("/projects/{testing_id}/plan-labels/order", response_model=list[PlanLabelItem])
def patch_plan_label_order(
    testing_id: int,
    payload: PlanLabelOrderUpdate,
    db: Session = Depends(get_db),
) -> list[PlanLabelItem]:
    return update_plan_label_order(db, testing_id, payload)


@router.delete("/projects/{testing_id}/labels", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_label_route(
    testing_id: int,
    label: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> None:
    delete_project_label(db, testing_id, label.strip())


@router.patch("/plan-labels/{label_id}", response_model=PlanLabelItem)
def patch_plan_label(
    label_id: int,
    payload: PlanLabelUpdate,
    db: Session = Depends(get_db),
) -> PlanLabelItem:
    return update_plan_label(db, label_id, payload)


@router.delete("/plan-labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_label_route(label_id: int, db: Session = Depends(get_db)) -> None:
    delete_plan_label(db, label_id)


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
