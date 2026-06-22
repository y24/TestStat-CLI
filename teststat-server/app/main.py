from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.routers import (
    azure_devops_router,
    bug_router,
    collect_router,
    holiday_router,
    progress_router,
    project_router,
    plan_router,
    setting_router,
)

settings = get_settings()

app = FastAPI(title="TestStat Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(progress_router)
app.include_router(project_router)
app.include_router(plan_router)
app.include_router(holiday_router)
app.include_router(setting_router)
app.include_router(azure_devops_router)
app.include_router(bug_router)
app.include_router(collect_router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}

