from __future__ import annotations

import re
from typing import Any

from app.db.models import ReportRawMeta

STANDARD_COMPANY_CODE_PATTERN = re.compile(r"^\d{6}$")


def normalize_report_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def is_ipo_report(company_code: str | None, report_title: str | None) -> bool:
    normalized_code = normalize_report_text(company_code)
    normalized_title = normalize_report_text(report_title)

    if normalized_code and not STANDARD_COMPANY_CODE_PATTERN.fullmatch(normalized_code):
        return True

    if normalized_title and "IPO" in normalized_title.upper():
        return True

    return False


def is_ipo_report_row(row: dict[str, Any]) -> bool:
    return is_ipo_report(
        company_code=normalize_report_text(row.get("company_code")),
        report_title=normalize_report_text(row.get("report_title")),
    )


def is_ipo_report_model(row: ReportRawMeta) -> bool:
    return is_ipo_report(
        company_code=normalize_report_text(row.company_code),
        report_title=normalize_report_text(row.report_title),
    )


def filter_non_ipo_report_models(rows: list[ReportRawMeta]) -> list[ReportRawMeta]:
    return [row for row in rows if not is_ipo_report_model(row)]
