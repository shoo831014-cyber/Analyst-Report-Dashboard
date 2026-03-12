import logging
import logging.config
from pathlib import Path


def configure_logging(log_level: str, log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / "app.log"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": log_level,
                },
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(logfile),
                    "formatter": "standard",
                    "level": log_level,
                    "encoding": "utf-8",
                },
            },
            "root": {"handlers": ["console", "file"], "level": log_level},
        }
    )
    logging.getLogger(__name__).info("Logging configured")

