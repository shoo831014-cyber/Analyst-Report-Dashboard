from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import ReportRawMeta
from app.db.session import get_db_session
from app.services.report_case_utils import dedupe_company_provider_cases
from app.services.report_filter_utils import filter_non_ipo_report_models

router = APIRouter(tags=["reports"])


@router.get("/api/v1/reports")
def get_reports(
    date_param: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, ge=1, le=500),
    company_code: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> dict:
    target_date = date_param
    if target_date is None:
        target_date = db.scalar(select(func.max(ReportRawMeta.snapshot_date)))

    if target_date is None:
        return {"snapshot_date": None, "total": 0, "items": []}

    base_query = select(ReportRawMeta).where(ReportRawMeta.snapshot_date == target_date)
    if company_code:
        base_query = base_query.where(ReportRawMeta.company_code == company_code)

    rows = db.scalars(
        base_query.order_by(desc(ReportRawMeta.report_date), desc(ReportRawMeta.id))
    ).all()
    rows = filter_non_ipo_report_models(rows)
    deduped_rows = sorted(
        dedupe_company_provider_cases(rows),
        key=lambda row: ((row.report_date or row.snapshot_date), row.id or 0),
        reverse=True,
    )
    total = len(deduped_rows)

    return {
        "snapshot_date": target_date.isoformat(),
        "total": total,
        "items": [
            {
                "id": row.id,
                "snapshot_date": row.snapshot_date.isoformat(),
                "report_date": row.report_date.isoformat() if row.report_date else None,
                "company_code": row.company_code,
                "company_name": row.company_name,
                "report_title": row.report_title,
                "analyst_name": row.analyst_name,
                "provider_name": row.provider_name,
                "opinion_raw": row.opinion_raw,
                "opinion_std": row.opinion_std,
                "target_price_raw": row.target_price_raw,
                "target_price_value": row.target_price_value,
                "prev_close_price_raw": row.prev_close_price_raw,
                "prev_close_price_value": row.prev_close_price_value,
                "source_url": row.source_url,
                "collected_at": row.collected_at.isoformat() if row.collected_at else None,
            }
            for row in deduped_rows[:limit]
        ],
    }
