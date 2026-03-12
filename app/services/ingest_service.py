from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.fnguide.client import FnGuideCollector
from app.collectors.fnguide.parser_requests import normalize_text, parse_date_value
from app.collectors.fnguide.selectors import MAX_ALLOWED_MISSING_RATIO, build_report_reference_url
from app.db import session as db_session
from app.db.base import Base
from app.db.models import CompanyMaster, JobRun, ReportRawMeta
from app.domain.calculators import calculate_upside, safe_to_int
from app.domain.opinion_mapper import normalize_opinion
from app.domain.schemas import IngestSummary
from app.services.report_filter_utils import is_ipo_report_row
from app.services.report_summary_utils import parse_summary_lines

logger = logging.getLogger(__name__)

IR_ANALYST_MARKERS = {"ir\ud300", "ir team", "irteam"}
IR_PROVIDER_MARKERS = {"\ud574\ub2f9\uae30\uc5c5", "\uc790\uc0ac", "\ub2f9\uc0ac"}


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def should_fallback(rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return True

    required_missing = sum(
        1
        for row in rows
        if not normalize_text(row.get("report_title")) or not normalize_text(row.get("company_name"))
    )
    missing_ratio = required_missing / len(rows)
    if missing_ratio > MAX_ALLOWED_MISSING_RATIO:
        return True

    if all(not normalize_text(row.get("company_code")) for row in rows):
        return True

    return False


def is_ir_authored_row(row: dict[str, Any]) -> bool:
    analyst_name = (normalize_text(row.get("analyst_name")) or "").strip().lower()
    provider_name = (normalize_text(row.get("provider_name")) or "").strip().lower()

    if analyst_name in IR_ANALYST_MARKERS:
        return True

    if provider_name in IR_PROVIDER_MARKERS:
        return True

    return False


class IngestService:
    def __init__(
        self,
        collector: FnGuideCollector | None = None,
        session_factory: Any | None = None,
    ) -> None:
        self.collector = collector or FnGuideCollector()
        self.session_factory = session_factory or db_session.SessionLocal

    def run(self, snapshot_date: date) -> IngestSummary:
        with self.session_factory() as session:
            bind = session.get_bind()
            if bind is not None:
                db_session.ensure_schema(bind)
            job_run = self._start_job(session, snapshot_date)
            try:
                requested_rows = self.collector.fetch_with_requests(snapshot_date)
                fallback_used = should_fallback(requested_rows)
                source = "requests"

                logger.info(
                    "FnGuide ingest fetched via requests. snapshot_date=%s rows=%s fallback=%s",
                    snapshot_date.isoformat(),
                    len(requested_rows),
                    fallback_used,
                )

                rows = requested_rows
                if fallback_used:
                    source = "playwright"
                    rows = self.collector.fetch_with_playwright(snapshot_date)
                    logger.info(
                        "FnGuide ingest fallback executed. snapshot_date=%s rows=%s",
                        snapshot_date.isoformat(),
                        len(rows),
                    )

                normalized_rows, invalid_rows, upside_ready_count, filtered_ir_rows, filtered_ipo_rows = self._normalize_rows(rows, snapshot_date)
                inserted, skipped = self._persist_reports(session, normalized_rows)
                session.commit()

                message = (
                    f"source={source} fetched={len(rows)} inserted={inserted} "
                    f"skipped={skipped} invalid={invalid_rows} filtered_ir={filtered_ir_rows} "
                    f"filtered_ipo={filtered_ipo_rows} fallback={fallback_used}"
                )
                summary = IngestSummary(
                    snapshot_date=snapshot_date,
                    source=source,
                    fallback_used=fallback_used,
                    fetched=len(rows),
                    filtered_ir=filtered_ir_rows,
                    filtered_ipo=filtered_ipo_rows,
                    inserted=inserted,
                    skipped=skipped,
                    errors=invalid_rows,
                    upside_ready_count=upside_ready_count,
                    job_run_id=job_run.id,
                    message=message,
                )
                self._finish_job(session, job_run, "SUCCESS", message)
                logger.info("FnGuide ingest completed. %s", message)
                return summary
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                message = f"source=fnguide status=FAILED error={exc}"
                self._finish_job(session, job_run, "FAILED", message)
                logger.exception("FnGuide ingest failed. snapshot_date=%s", snapshot_date.isoformat())
                raise

    def _normalize_rows(
        self,
        rows: list[dict[str, Any]],
        snapshot_date: date,
    ) -> tuple[list[dict[str, Any]], int, int, int, int]:
        normalized: list[dict[str, Any]] = []
        invalid_rows = 0
        upside_ready_count = 0
        filtered_ir_rows = 0
        filtered_ipo_rows = 0

        for row in rows:
            if is_ir_authored_row(row):
                filtered_ir_rows += 1
                continue
            if is_ipo_report_row(row):
                filtered_ipo_rows += 1
                continue
            company_code = normalize_text(row.get("company_code"))
            company_name = normalize_text(row.get("company_name"))
            report_title = normalize_text(row.get("report_title"))
            if not company_code or not company_name or not report_title:
                invalid_rows += 1
                continue

            report_date = row.get("report_date")
            if isinstance(report_date, str):
                report_date = parse_date_value(report_date)

            opinion_raw = normalize_text(row.get("opinion_raw"))
            target_price_raw = normalize_text(row.get("target_price_raw"))
            prev_close_price_raw = normalize_text(row.get("prev_close_price_raw"))
            target_price_value = safe_to_int(target_price_raw)
            prev_close_price_value = safe_to_int(prev_close_price_raw)
            upside_pct = calculate_upside(target_price_value, prev_close_price_value)
            if upside_pct is not None:
                upside_ready_count += 1

            report_id = normalize_text(row.get("report_id"))
            source_url = normalize_text(row.get("source_url")) or build_report_reference_url(company_code, report_id)
            dedupe_key = self._build_dedupe_key(
                snapshot_date=snapshot_date,
                report_date=report_date,
                company_code=company_code,
                report_title=report_title,
                provider_name=normalize_text(row.get("provider_name")),
                analyst_name=normalize_text(row.get("analyst_name")),
                source_url=source_url,
                report_id=report_id,
            )

            normalized.append(
                {
                    "snapshot_date": snapshot_date,
                    "report_date": report_date,
                    "company_code": company_code,
                    "company_name": company_name,
                    "report_title": report_title,
                    "summary_lines_json": parse_summary_lines(row.get("summary_lines")),
                    "analyst_name": normalize_text(row.get("analyst_name")),
                    "provider_name": normalize_text(row.get("provider_name")),
                    "opinion_raw": opinion_raw,
                    "opinion_std": normalize_opinion(opinion_raw),
                    "target_price_raw": target_price_raw,
                    "target_price_value": target_price_value,
                    "prev_close_price_raw": prev_close_price_raw,
                    "prev_close_price_value": prev_close_price_value,
                    "source_url": source_url,
                    "collected_at": utcnow_naive(),
                    "dedupe_key": dedupe_key,
                }
            )

        return normalized, invalid_rows, upside_ready_count, filtered_ir_rows, filtered_ipo_rows

    def _persist_reports(self, session: Session, rows: list[dict[str, Any]]) -> tuple[int, int]:
        if not rows:
            return 0, 0

        dedupe_keys = [row["dedupe_key"] for row in rows]
        existing_reports = session.scalars(
            select(ReportRawMeta).where(ReportRawMeta.dedupe_key.in_(dedupe_keys))
        ).all()
        existing_map = {row.dedupe_key: row for row in existing_reports}
        existing_keys = set(existing_map)

        batch_seen: set[str] = set()
        reports_to_insert: list[ReportRawMeta] = []
        companies_to_insert: dict[str, str] = {}
        inserted = 0
        skipped = 0

        for row in rows:
            dedupe_key = row["dedupe_key"]
            if dedupe_key in existing_keys or dedupe_key in batch_seen:
                existing = existing_map.get(dedupe_key)
                if existing is not None and row.get("summary_lines_json") and not existing.summary_lines_json:
                    existing.summary_lines_json = row["summary_lines_json"]
                skipped += 1
                continue

            batch_seen.add(dedupe_key)
            reports_to_insert.append(ReportRawMeta(**row))
            inserted += 1
            companies_to_insert[row["company_code"]] = row["company_name"]

        if reports_to_insert:
            session.add_all(reports_to_insert)
            self._upsert_company_master(session, companies_to_insert)

        return inserted, skipped

    def _upsert_company_master(self, session: Session, companies: dict[str, str]) -> None:
        if not companies:
            return

        existing_codes = set(
            session.scalars(
                select(CompanyMaster.company_code).where(CompanyMaster.company_code.in_(tuple(companies.keys())))
            ).all()
        )

        for company_code, company_name in companies.items():
            if company_code in existing_codes:
                existing = session.get(CompanyMaster, company_code)
                if existing and existing.company_name != company_name:
                    existing.company_name = company_name
                    existing.updated_at = utcnow_naive()
                continue

            session.add(
                CompanyMaster(
                    company_code=company_code,
                    company_name=company_name,
                    sector_name_fnguide=None,
                    is_active=True,
                    updated_at=utcnow_naive(),
                )
            )

    def _start_job(self, session: Session, snapshot_date: date) -> JobRun:
        job_run = JobRun(
            job_name="fnguide_ingest",
            run_status="RUNNING",
            started_at=utcnow_naive(),
            message=f"snapshot_date={snapshot_date.isoformat()}",
        )
        session.add(job_run)
        session.commit()
        session.refresh(job_run)
        return job_run

    def _finish_job(self, session: Session, job_run: JobRun, status: str, message: str) -> None:
        job_run.run_status = status
        job_run.finished_at = utcnow_naive()
        job_run.message = message
        session.add(job_run)
        session.commit()

    def _build_dedupe_key(
        self,
        *,
        snapshot_date: date,
        report_date: date | None,
        company_code: str,
        report_title: str,
        provider_name: str | None,
        analyst_name: str | None,
        source_url: str | None,
        report_id: str | None,
    ) -> str:
        canonical = "|".join(
            [
                snapshot_date.isoformat(),
                report_date.isoformat() if report_date else "",
                company_code,
                (report_title or "").strip().lower(),
                (provider_name or "").strip().lower(),
                (analyst_name or "").strip().lower(),
                (report_id or "").strip().lower(),
                (source_url or "").strip().lower(),
            ]
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
