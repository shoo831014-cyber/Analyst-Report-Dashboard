from app.domain.calculators import calculate_upside


def test_calculate_upside_basic() -> None:
    assert calculate_upside(12000, 10000) == 20.0


def test_calculate_upside_none_or_zero() -> None:
    assert calculate_upside(None, 10000) is None
    assert calculate_upside(12000, None) is None
    assert calculate_upside(12000, 0) is None

