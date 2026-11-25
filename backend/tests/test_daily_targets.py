from decimal import Decimal

from app.services.daily_targets import carb_servings, daily_targets, meal_targets


def test_daily_targets_uses_midpoint_macro_ratios() -> None:
    targets = daily_targets(Decimal(160), Decimal(55), "中")
    assert targets is not None
    assert targets.daily_kcal == 1650
    assert targets.carb_g == Decimal("206.25")
    assert targets.protein_g == Decimal("74.25")
    assert targets.fat_g == Decimal("58.67")


def test_meal_targets_split_30_40_30() -> None:
    targets = daily_targets(Decimal(160), Decimal(55), "中")
    assert targets is not None
    breakfast = meal_targets(targets, "早餐")
    lunch = meal_targets(targets, "午餐")
    dinner = meal_targets(targets, "晚餐")
    assert breakfast is not None
    assert lunch is not None
    assert dinner is not None
    assert breakfast.kcal == Decimal("495.00")
    assert breakfast.carb_g == Decimal("61.88")
    assert lunch.kcal == Decimal("660.00")
    assert lunch.carb_g == Decimal("82.50")
    assert dinner.carb_g == Decimal("61.88")


def test_carb_servings_rounds_to_half() -> None:
    assert carb_servings(Decimal("61.88")) == 4.0
    assert carb_servings(Decimal("82.50")) == 5.5
    assert carb_servings(Decimal("45")) == 3.0
    assert carb_servings(None) is None


def test_snack_or_unknown_meal_returns_none() -> None:
    targets = daily_targets(Decimal(160), Decimal(55), "中")
    assert targets is not None
    assert meal_targets(targets, "加餐") is None
    assert meal_targets(targets, None) is None


def test_missing_body_fields_return_none() -> None:
    assert daily_targets(None, Decimal(55), "中") is None
    assert daily_targets(Decimal(160), None, "中") is None
    assert daily_targets(Decimal(160), Decimal(55), "") is None
