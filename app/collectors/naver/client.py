from __future__ import annotations

from datetime import date
from typing import Any

from app.collectors.base import BaseCollector


class NaverCollector(BaseCollector):
    source_name = "naver_research"

    def collect(self, snapshot_date: date) -> list[dict[str, Any]]:
        # TODO: implement in future phase for report original content metadata.
        return []

