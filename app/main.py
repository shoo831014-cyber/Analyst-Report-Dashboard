from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_health import router as health_router
from app.api.routes_reports import router as reports_router
from app.config import get_settings
from app.db.session import init_db
from app.logging_config import configure_logging
from app.runtime_paths import get_static_dir


def ensure_runtime_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    configure_logging(settings.log_level, settings.log_path)
    ensure_runtime_dirs([settings.export_path, settings.snapshot_path, settings.log_path])
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    ensure_runtime_dirs([settings.export_path, settings.snapshot_path, settings.log_path])
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(get_static_dir())), name="static")
    app.mount("/exports", StaticFiles(directory=str(settings.export_path), html=True), name="exports")

    app.include_router(health_router)
    app.include_router(dashboard_router)
    app.include_router(reports_router)

    @app.get("/", include_in_schema=False)
    def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    return app


app = create_app()
