from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, date, datetime

from app.config import get_settings
from app.logging_config import configure_logging
from app.services.ingest_service import IngestService

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_path)

    snapshot_date = _parse_args().date or date.today()
    service = IngestService()

    logger.info("FnGuide ingest job started. snapshot_date=%s", snapshot_date.isoformat())
    started_at = utcnow_naive()
    try:
        summary = service.run(snapshot_date=snapshot_date)
        logger.info("FnGuide ingest job success. %s", summary.message)
        print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    except Exception:  # noqa: BLE001
        logger.exception("FnGuide ingest job failed. snapshot_date=%s", snapshot_date.isoformat())
        raise
    finally:
        finished_at = utcnow_naive()
        logger.info(
            "FnGuide ingest job finished. snapshot_date=%s started_at=%s finished_at=%s",
            snapshot_date.isoformat(),
            started_at.isoformat(),
            finished_at.isoformat(),
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FnGuide report metadata ingest")
    parser.add_argument("--date", type=_parse_date, help="Snapshot date in YYYY-MM-DD format")
    return parser.parse_args()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


if __name__ == "__main__":
    main()
