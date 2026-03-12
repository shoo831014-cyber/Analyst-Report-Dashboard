from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def main() -> None:
    threshold_date = date.today() - timedelta(days=90)
    # TODO: Step 8 - delete snapshot/export files and DB rows older than threshold.
    logger.info("Cleanup placeholder executed. threshold_date=%s", threshold_date.isoformat())


if __name__ == "__main__":
    main()

