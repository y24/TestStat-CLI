from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud.project import create_project, delete_project, get_project, list_projects, update_project, update_project_order
from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectOrderUpdate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def read_projects(db: Session = Depends(get_db)) -> list[ProjectResponse]:
    return list_projects(db)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def post_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectResponse:
    return create_project(db, payload)


@router.patch("/order", response_model=list[ProjectResponse])
def patch_project_order(payload: ProjectOrderUpdate, db: Session = Depends(get_db)) -> list[ProjectResponse]:
    return update_project_order(db, payload)


@router.get("/{testing_id}", response_model=ProjectResponse)
def read_project(testing_id: int, db: Session = Depends(get_db)) -> ProjectResponse:
    return get_project(db, testing_id)


@router.patch("/{testing_id}", response_model=ProjectResponse)
def patch_project(testing_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)) -> ProjectResponse:
    return update_project(db, testing_id, payload)


@router.delete("/{testing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_route(testing_id: int, db: Session = Depends(get_db)) -> None:
    delete_project(db, testing_id)
