from app.models import LevelCurve, calculate_level

CURVE = LevelCurve(
    base_units_per_level=100,
    growth_units_per_level=50,
    growth_interval_levels=2,
    max_level=5,
)


def test_starts_at_level_one() -> None:
    level, remaining = calculate_level(0, CURVE)
    assert level == 1
    assert remaining == 100


def test_levels_up_exactly_at_threshold() -> None:
    level, remaining = calculate_level(100, CURVE)
    assert level == 2
    # レベル2はまだtier0（growth_interval_levels=2以内）なので、
    # 次のレベルまでの必要時間もbase_units_per_level(100)のまま
    assert remaining == 100


def test_growth_increases_after_interval() -> None:
    # レベル3(=growth_interval_levels=2を超えた最初のtier)からは
    # base(100) + growth(50) = 150 必要になる
    level, remaining = calculate_level(200, CURVE)
    assert level == 3
    assert remaining == 150


def test_caps_at_max_level() -> None:
    level, remaining = calculate_level(10_000, CURVE)
    assert level == 5
    assert remaining == 0


def test_never_exceeds_max_level_even_with_huge_total() -> None:
    level, _ = calculate_level(1_000_000_000, CURVE)
    assert level == CURVE.max_level
