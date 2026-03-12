from __future__ import annotations

import re
from typing import Any

BULLET_PREFIX_PATTERN = re.compile(r"^[▶•▪■·\-\*]+\s*")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_summary_line(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).replace("\xa0", " ").replace("\r", " ").replace("\n", " ")
    text = WHITESPACE_PATTERN.sub(" ", text).strip()
    text = BULLET_PREFIX_PATTERN.sub("", text).strip()
    return text or None


def parse_summary_lines(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        candidates = value
    else:
        candidates = str(value).splitlines()

    lines: list[str] = []
    for candidate in candidates:
        normalized = normalize_summary_line(candidate)
        if normalized:
            lines.append(normalized)
    return lines


def dedupe_summary_lines(lines: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for line in lines:
        normalized = normalize_summary_line(line)
        if not normalized:
            continue

        key = normalized.rstrip(".").lower()
        if key in seen:
            continue

        seen.add(key)
        deduped.append(normalized)

    return deduped
