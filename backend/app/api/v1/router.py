from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.routers.projects import router as projects_router
from app.api.v1.routers.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(ws_router, prefix="/ws/projects", tags=["websockets"])
