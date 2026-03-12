from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, date, datetime
from typing import Any

from app.config import get_settings
from app.db import session as db_session
from app.db.models import JobRun
from app.db.session import SessionLocal
from app.logging_config import configure_logging
from app.services.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def main(
    snapshot_date: date | None = None,
    *,
    session_factory: Any | None = None,
    service: SnapshotService | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_path)

    resolved_session_factory = session_factory or SessionLocal
    snapshot_service = service or SnapshotService(session_factory=resolved_session_factory)

    with resolved_session_factory() as session:
        bind = session.get_bind()
        if bind is not None:
            db_session.ensure_schema(bind)

        target_date = snapshot_date or _parse_args().date
        if target_date is None:
            target_date = snapshot_service.get_latest_raw_snapshot_date(session)
        if target_date is None:
            raise ValueError("No raw snapshot_date available to publish.")

        job_run = JobRun(
            job_name="dashboard_publish",
            run_status="RUNNING",
            started_at=utcnow_naive(),
            message=f"snapshot_date={target_date.isoformat()}",
        )
        session.add(job_run)
        session.commit()
        session.refresh(job_run)

        logger.info("Publish job started. snapshot_date=%s", target_date.isoformat())
        try:
            result = snapshot_service.rebuild_snapshot_for_date(session, target_date)
            message = (
                f"snapshot_date={target_date.isoformat()} "
                f"raw_reports={result['raw_reports']} "
                f"company_summaries={result['company_summaries']} "
                f"sector_summaries={result['sector_summaries']}"
            )

            job_run.run_status = "SUCCESS"
            job_run.finished_at = utcnow_naive()
            job_run.message = message
            session.add(job_run)
            session.commit()

            logger.info("Publish job success. %s", message)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            job_run.run_status = "FAILED"
            job_run.finished_at = utcnow_naive()
            job_run.message = f"snapshot_date={target_date.isoformat()} error={exc}"
            session.add(job_run)
            session.commit()
            logger.exception("Publish job failed. snapshot_date=%s", target_date.isoformat())
            raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild dashboard snapshot for a date")
    parser.add_argument("--date", type=_parse_date, help="Snapshot date in YYYY-MM-DD format")
    return parser.parse_args()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


if __name__ == "__main__":
    main()
