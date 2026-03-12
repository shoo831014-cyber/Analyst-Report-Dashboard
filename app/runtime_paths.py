from __future__ import annotations

import sys
from pathlib import Path


def get_bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_templates_dir() -> Path:
    return get_bundle_root() / "app" / "templates"


def get_static_dir() -> Path:
    return get_bundle_root() / "app" / "static"
