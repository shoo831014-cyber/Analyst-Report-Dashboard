from __future__ import annotations

from datetime import date


def get_recent_snapshot_dates(dates: list[date], limit: int = 5) -> list[date]:
    if limit <= 0:
        return []
    unique_sorted = sorted(set(dates), reverse=True)
    return unique_sorted[:limit]

