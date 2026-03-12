from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class BaseCollector(ABC):
    source_name: str

    @abstractmethod
    def collect(self, snapshot_date: date) -> list[dict[str, Any]]:
        """Collect and return normalized rows."""

