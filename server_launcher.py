from __future__ import annotations

import os
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from app.config import get_settings


def _resolve_runtime_dir() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _open_dashboard(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


def main() -> None:
    runtime_dir = _resolve_runtime_dir()
    os.chdir(runtime_dir)

    get_settings.cache_clear()
    settings = get_settings()

    from app.main import app

    dashboard_url = f"http://{settings.app_host}:{settings.app_port}/dashboard"
    threading.Thread(target=_open_dashboard, args=(dashboard_url,), daemon=True).start()

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
