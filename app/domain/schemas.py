from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


class DashboardSummaryResponse(BaseModel):
    snapshot_date: date | None
    total_reports: int
    buy_reports: int
    hold_reports: int
    sell_reports: int
    nr_reports: int
    top3_companies: list[dict[str, Any]]


class IngestSummary(BaseModel):
    snapshot_date: date
    source: str
    fallback_used: bool
    fetched: int
    filtered_ir: int = 0
    filtered_ipo: int = 0
    inserted: int
    skipped: int
    errors: int
    upside_ready_count: int
    job_run_id: int | None = None
    message: str
