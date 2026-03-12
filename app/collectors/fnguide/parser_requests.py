from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup

from app.collectors.fnguide.selectors import (
    MIN_EXPECTED_COLUMNS,
    NO_DATA_TEXTS,
    REPORT_ROW_SELECTORS,
    REQUIRED_ROW_FIELDS,
    build_report_reference_url,
)
from app.services.report_summary_utils import parse_summary_lines


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).replace("\xa0", " ").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    return text or None


def parse_date_value(value: Any) -> date | None:
    text = normalize_text(value)
    if not text:
        return None

    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_report_rows(payload: str) -> list[dict[str, Any]]:
    if not payload or not payload.strip():
        return []

    stripped = payload.lstrip()
    if stripped.startswith("{"):
        return _parse_json_rows(payload)
    if stripped.startswith("<"):
        return _parse_html_rows(payload)
    return []


def has_required_fields(row: dict[str, Any]) -> bool:
    return all(normalize_text(row.get(field)) for field in REQUIRED_ROW_FIELDS)


def _parse_json_rows(payload: str) -> list[dict[str, Any]]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return []

    dataset = decoded.get("dataset") or {}
    raw_rows = dataset.get("data") or decoded.get("data") or []
    if not isinstance(raw_rows, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        report_id = item.get("RPT_ID")
        company_code = normalize_text(item.get("CMP_CD"))
        rows.append(
            {
                "report_id": report_id,
                "report_date": parse_date_value(item.get("DT")),
                "company_code": company_code,
                "company_name": normalize_text(item.get("CMP_NM_KOR")),
                "report_title": normalize_text(item.get("RPT_TITLE")),
                "summary_lines": parse_summary_lines(item.get("COMMENT")),
                "analyst_name": normalize_text(item.get("ANL_NM_KOR")),
                "provider_name": normalize_text(item.get("BRK_NM_KOR")),
                "opinion_raw": normalize_text(item.get("RECOMM_NM")),
                "target_price_raw": normalize_text(item.get("TARGET_PRC")),
                "prev_close_price_raw": normalize_text(item.get("CLOSE_PRC")),
                "source_url": build_report_reference_url(company_code, report_id),
            }
        )
    return rows


def _parse_html_rows(payload: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(payload, "lxml")
    for selector in REPORT_ROW_SELECTORS:
        rows = _extract_rows_from_selector(soup, selector)
        if rows:
            return rows
    return []


def _extract_rows_from_selector(soup: BeautifulSoup, selector: str) -> list[dict[str, Any]]:
    parsed_rows: list[dict[str, Any]] = []
    for row in soup.select(selector):
        text = normalize_text(row.get_text(" ", strip=True))
        if text in NO_DATA_TEXTS:
            continue

        cells = row.select("td")
        if len(cells) < MIN_EXPECTED_COLUMNS:
            continue

        report_id = normalize_text(row.get("data-rpt_id"))
        company_code = normalize_text(row.get("data-cmp_cd"))

        company_link = row.select_one("a.snapshotLink")
        code_el = company_link.select_one(".txt1") if company_link else None
        if not company_code and code_el:
            company_code = normalize_text(code_el.get_text(" ", strip=True))

        company_name = None
        if company_link:
            company_name = _extract_company_name(company_link, company_code)

        title_el = row.select_one("span.txt2")
        report_title = normalize_text(title_el.get_text(" ", strip=True) if title_el else None)
        if report_title and report_title.startswith("-"):
            report_title = normalize_text(report_title.lstrip("-"))

        provider_analyst = [normalize_text(value) for value in cells[5].stripped_strings]
        provider_analyst = [value for value in provider_analyst if value]

        parsed_row = {
            "report_id": report_id,
            "report_date": parse_date_value(cells[0].get_text(" ", strip=True)),
            "company_code": company_code,
            "company_name": company_name,
            "report_title": report_title,
            "summary_lines": [],
            "analyst_name": provider_analyst[1] if len(provider_analyst) > 1 else None,
            "provider_name": provider_analyst[0] if provider_analyst else None,
            "opinion_raw": normalize_text(cells[2].get_text(" ", strip=True)),
            "target_price_raw": normalize_text(cells[3].get_text(" ", strip=True)),
            "prev_close_price_raw": normalize_text(cells[4].get_text(" ", strip=True)),
            "source_url": build_report_reference_url(company_code, report_id),
        }

        if has_required_fields(parsed_row):
            parsed_rows.append(parsed_row)

    return parsed_rows


def _extract_company_name(company_link: Any, company_code: str | None) -> str | None:
    primary_text = normalize_text(company_link.contents[0] if company_link.contents else None)
    if primary_text:
        return primary_text

    text = normalize_text(company_link.get_text(" ", strip=True))
    if not text:
        return None
    if company_code and text.endswith(company_code):
        trimmed = normalize_text(text[: -len(company_code)])
        if trimmed:
            return trimmed
    return text
