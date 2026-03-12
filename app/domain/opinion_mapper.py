from __future__ import annotations


BUY_KEYWORDS = {
    "buy",
    "\ub9e4\uc218",
    "strong buy",
    "outperform",
    "overweight",
    "\ube44\uc911\ud655\ub300",
}
HOLD_KEYWORDS = {
    "hold",
    "\uc911\ub9bd",
    "neutral",
    "market perform",
    "trading buy",
}
SELL_KEYWORDS = {
    "sell",
    "\ub9e4\ub3c4",
    "underperform",
    "underweight",
    "\ube44\uc911\ucd95\uc18c",
    "reduce",
}
NR_KEYWORDS = {
    "nr",
    "not rated",
    "\uc758\uacac\uc5c6\uc74c",
    "\ubbf8\uc81c\uc2dc",
    "\uae30\ud0c0",
}


def normalize_opinion(raw: str | None) -> str:
    if not raw:
        return "NR"

    value = " ".join(raw.strip().lower().split())
    if not value:
        return "NR"

    if value in BUY_KEYWORDS:
        return "BUY"
    if value in HOLD_KEYWORDS:
        return "HOLD"
    if value in SELL_KEYWORDS:
        return "SELL"
    if value in NR_KEYWORDS:
        return "NR"

    if any(keyword in value for keyword in ("buy", "\ub9e4\uc218", "outperform", "overweight", "\ube44\uc911\ud655\ub300")):
        return "BUY"
    if any(keyword in value for keyword in ("hold", "\uc911\ub9bd", "neutral", "market perform", "trading buy")):
        return "HOLD"
    if any(
        keyword in value
        for keyword in ("sell", "\ub9e4\ub3c4", "underperform", "underweight", "\ube44\uc911\ucd95\uc18c", "reduce")
    ):
        return "SELL"
    return "NR"
