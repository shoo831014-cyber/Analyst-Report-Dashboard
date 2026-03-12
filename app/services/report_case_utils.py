from __future__ import annotations

from datetime import date, datetime

from app.db.models import ReportRawMeta


def dedupe_company_provider_cases(rows: list[ReportRawMeta]) -> list[ReportRawMeta]:
    deduped: dict[tuple[str, str], ReportRawMeta] = {}
    for row in rows:
        key = (row.company_code, provider_case_key(row))
        current = deduped.get(key)
        if current is None or row_priority(row) > row_priority(current):
            deduped[key] = row

    return sorted(
        deduped.values(),
        key=lambda row: (row.company_code, provider_case_key(row), row.id or 0),
    )


def provider_case_key(row: ReportRawMeta) -> str:
    provider_name = (row.provider_name or "").strip().lower()
    return provider_name if provider_name else f"__row__:{row.id or 0}"


def row_priority(row: ReportRawMeta) -> tuple[date, datetime, int]:
    return (
        row.report_date or row.snapshot_date,
        row.collected_at or datetime.min,
        row.id or 0,
    )
