from app.domain.opinion_mapper import normalize_opinion


def test_normalize_opinion_buy() -> None:
    assert normalize_opinion("\ub9e4\uc218") == "BUY"
    assert normalize_opinion("Outperform") == "BUY"


def test_normalize_opinion_hold_sell_nr() -> None:
    assert normalize_opinion("Neutral") == "HOLD"
    assert normalize_opinion("Underweight") == "SELL"
    assert normalize_opinion("\ubbf8\uc81c\uc2dc") == "NR"
    assert normalize_opinion(None) == "NR"
