from app.routers.progress import router as progress_router
from app.routers.project import router as project_router
from app.routers.plan import router as plan_router
from app.routers.holiday import router as holiday_router
from app.routers.setting import router as setting_router
from app.routers.azure_devops import router as azure_devops_router
from app.routers.bug import router as bug_router

__all__ = [
    "progress_router",
    "project_router",
    "plan_router",
    "holiday_router",
    "setting_router",
    "azure_devops_router",
    "bug_router",
]
