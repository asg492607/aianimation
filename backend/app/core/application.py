from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.router import api_router

# Path where frontend static files are copied in the Docker image
STATIC_DIR = Path("/app/static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI Animation Generator Platform API",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
        redirect_slashes=True,
    )

    # ── Health checks ─────────────────────────────────────────────────────────
    @application.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    # ── Middlewares ───────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    # ── API routes ────────────────────────────────────────────────────────────
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # ── Serve frontend static files ───────────────────────────────────────────
    # Only mount if the static dir exists (it's copied in by Docker)
    if STATIC_DIR.exists():
        application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        # Serve index.html at the root and for any unknown path (SPA fallback)
        @application.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(str(STATIC_DIR / "index.html"))

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # Try to serve an exact file first (e.g. style.css, app.js)
            requested = STATIC_DIR / full_path
            if requested.exists() and requested.is_file():
                return FileResponse(str(requested))
            # Fallback: return index.html for client-side routing
            return FileResponse(str(STATIC_DIR / "index.html"))

    return application
