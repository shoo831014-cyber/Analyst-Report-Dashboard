from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.runtime_paths import get_templates_dir
from app.services.export_service import ExportService
from app.services.ingest_service import IngestService
from app.services.snapshot_service import SnapshotService

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(get_templates_dir()))
SEOUL_TIMEZONE = timezone(timedelta(hours=9))
ingest_service = IngestService()
snapshot_service = SnapshotService()
export_service = ExportService(snapshot_service=snapshot_service)


def current_seoul_date() -> date:
    return datetime.now(SEOUL_TIMEZONE).date()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    date_param: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db_session),
):
    context = snapshot_service.build_dashboard_view_model(db, date_param)
    context.update(
        {
            "request": request,
            "inline_css": None,
            "inline_js": None,
            "static_css_url": "/static/css/dashboard.css",
            "static_js_url": "/static/js/dashboard.js",
            "export_mode": False,
        }
    )
    return templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/api/v1/dashboard/summary")
def dashboard_summary(
    date_param: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db_session),
) -> dict:
    snapshot = snapshot_service.get_dashboard_snapshot(db, date_param)
    return snapshot_service.serialize_dashboard_snapshot(snapshot)


@router.get("/api/v1/dashboard/dates")
def dashboard_dates(
    limit: int = Query(default=5, ge=1, le=30),
    db: Session = Depends(get_db_session),
) -> dict[str, list[str]]:
    dates = snapshot_service.get_available_snapshot_dates(db, limit=limit)
    return {"dates": [value.isoformat() for value in dates]}


@router.get("/api/v1/dashboard/companies")
def dashboard_companies(
    date_param: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> dict:
    resolved_date = snapshot_service.resolve_snapshot_date(db, date_param)
    if resolved_date is None:
        return {"snapshot_date": None, "total": 0, "items": []}

    items = snapshot_service.get_company_summaries(db, resolved_date)
    return {
        "snapshot_date": resolved_date.isoformat(),
        "total": len(items),
        "items": [snapshot_service.serialize_company_model(item) for item in items[:limit]],
    }


@router.get("/api/v1/dashboard/sectors")
def dashboard_sectors(
    date_param: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> dict:
    resolved_date = snapshot_service.resolve_snapshot_date(db, date_param)
    if resolved_date is None:
        return {"snapshot_date": None, "total": 0, "items": []}

    items = snapshot_service.get_sector_summaries(db, resolved_date)
    return {
        "snapshot_date": resolved_date.isoformat(),
        "total": len(items),
        "items": [snapshot_service.serialize_sector_model(item) for item in items[:limit]],
    }


@router.get("/api/v1/dashboard/export")
def dashboard_export_info(
    date_param: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db_session),
) -> dict:
    return export_service.get_export_info(db, date_param)


@router.post("/api/v1/dashboard/update")
def dashboard_manual_update(
    db: Session = Depends(get_db_session),
) -> dict:
    snapshot_date = current_seoul_date()
    ingest_summary = ingest_service.run(snapshot_date=snapshot_date)
    publish_result = snapshot_service.publish(snapshot_date)

    export_service.export_dashboard_html(db, snapshot_date)
    db.commit()
    export_info = export_service.get_export_info(db, snapshot_date)
    snapshot = snapshot_service.get_dashboard_snapshot(db, snapshot_date)
    snapshot_payload = snapshot_service.serialize_dashboard_snapshot(snapshot)

    return {
        "snapshot_date": snapshot_date.isoformat(),
        "ingest": ingest_summary.model_dump(mode="json"),
        "publish": publish_result,
        "export": export_info,
        "last_updated_at": snapshot_payload["created_at"],
        "last_updated_text": snapshot_payload["created_at_text"],
    }
