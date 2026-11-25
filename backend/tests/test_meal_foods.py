"""自定义配餐：营养换算、热量估算与汇总。"""

from datetime import date
from decimal import Decimal

from app.models.entities import Food, FoodUnitConversion, MealFoodItem
from app.services.meal_foods import (
    _effective_kcal,
    _gi_weighted,
    _scaled,
    _totals,
    _view,
)


def _food(**overrides: object) -> Food:
    defaults: dict[str, object] = {
        "id": 1,
        "name": "鸡蛋",
        "category": "蛋类及其制品-鸡蛋",
        "kcal": Decimal("144"),
        "carb_g": Decimal("1.5"),
        "protein_g": Decimal("13.3"),
        "fat_g": Decimal("8.8"),
        "fiber_g": None,
        "sodium_mg": Decimal("130"),
        "gi": Decimal("0"),
        "per_g": Decimal("100"),
        "nutrient_source": "成分表",
        "gi_source": "GI 表",
    }
    defaults.update(overrides)
    return Food(**defaults)  # type: ignore[arg-type]


def test_effective_kcal_uses_table_value() -> None:
    assert _effective_kcal(_food(kcal=Decimal("144"))) == (Decimal("144"), False)


def test_effective_kcal_estimates_from_macros() -> None:
    food = _food(kcal=None, carb_g=Decimal("0"), protein_g=None, fat_g=Decimal("99.9"))
    kcal, estimated = _effective_kcal(food)
    assert estimated is True
    assert kcal == Decimal("899.10")


def test_effective_kcal_none_when_all_missing() -> None:
    food = _food(kcal=None, carb_g=None, protein_g=None, fat_g=None)
    assert _effective_kcal(food) == (None, False)


def test_scaled_half_for_50g_per100() -> None:
    assert _scaled(Decimal("144"), Decimal("50"), Decimal("100")) == Decimal("72.00")


def test_view_computes_scaled_nutrients() -> None:
    food = _food()
    conv = FoodUnitConversion(food_id=1, unit="颗", grams_per_unit=Decimal("50"))
    item = MealFoodItem(
        id=1,
        user_id=1,
        date=date(2026, 11, 25),
        meal_type="早餐",
        food_id=1,
        quantity=Decimal("1"),
        unit="颗",
    )
    view = _view(item, food, conv)
    assert view["grams"] == 50.0
    assert view["kcal"] == 72.0
    assert view["protein_g"] == 6.65
    assert view["kcal_estimated"] is False
    assert view["gi_band_label"] == "低"


def test_totals_sum_and_mark_incomplete() -> None:
    items: list[dict[str, object]] = [
        {"kcal": 10.0, "carb_g": 5.0, "protein_g": 1.0, "fat_g": 2.0, "fiber_g": None, "sodium_mg": 100.0},
        {"kcal": 20.0, "carb_g": None, "protein_g": 2.0, "fat_g": 3.0, "fiber_g": 1.0, "sodium_mg": 50.0},
    ]
    totals, incomplete = _totals(items)
    assert totals["kcal"] == 30.0
    assert totals["carb_g"] == 5.0
    assert totals["fiber_g"] == 1.0
    assert "carb_g" in incomplete
    assert "fiber_g" in incomplete


def test_gi_weighted_by_carb() -> None:
    items: list[dict[str, object]] = [
        {"gi": 20.0, "carb_g": 10.0},
        {"gi": 60.0, "carb_g": 10.0},
    ]
    assert _gi_weighted(items) == 40.0

