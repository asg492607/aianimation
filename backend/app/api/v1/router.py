from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.routers.projects import router as projects_router
from app.api.v1.routers.ws import router as ws_router
from app.api.v1.routers.templates import router as templates_router
from app.api.v1.routers.avatars import router as avatars_router
from app.api.v1.routers.voices import router as voices_router
from app.api.v1.routers.analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(ws_router, prefix="/ws/projects", tags=["websockets"])
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_router.include_router(avatars_router, prefix="/avatars", tags=["avatars"])
api_router.include_router(voices_router, prefix="/voices", tags=["voices"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
