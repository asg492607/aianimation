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

        @application.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(
                str(STATIC_DIR / "index.html"),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            requested = STATIC_DIR / full_path
            if requested.exists() and requested.is_file():
                # Cache JS/CSS for a short time, never cache HTML
                ext = requested.suffix.lower()
                cache = "no-cache, no-store, must-revalidate" if ext == ".html" else "public, max-age=60"
                return FileResponse(str(requested), headers={"Cache-Control": cache})
            return FileResponse(
                str(STATIC_DIR / "index.html"),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )

    return application
