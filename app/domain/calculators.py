from __future__ import annotations

from typing import Any


def safe_to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = str(value).strip()
    if not text:
        return None

    cleaned = (
        text.replace(",", "")
        .replace("\uc6d0", "")
        .replace("%", "")
        .replace("+", "")
        .replace("KRW", "")
        .replace("W", "")
        .strip()
    )

    if cleaned in {"-", "N/A", "na", "None"}:
        return None

    try:
        return int(float(cleaned))
    except ValueError:
        return None


def calculate_upside(target_price: int | None, prev_close: int | None) -> float | None:
    if target_price is None or prev_close is None:
        return None
    if prev_close <= 0:
        return None
    return round(((target_price - prev_close) / prev_close) * 100, 2)
