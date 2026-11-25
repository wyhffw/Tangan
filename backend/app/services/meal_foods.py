"""自定义配餐：自选食材 + 份量，按《中国食物成分表》算营养总和。

营养只来自 Food 表里的成分数字，不在这里编造。成分表里某项缺失时，
该项按「缺」处理并在汇总的 incomplete 中标注，不用 0 代替。
成分表热量缺失但脂肪等供能营养素齐全时，用供能系数（4/4/9）粗估，并标 kcal_estimated。
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import (
    Food,
    FoodUnitConversion,
    MealFoodItem,
    Recipe,
    RecipeIngredient,
)
from app.repositories.inventory import conversions_for, get_conversion, get_food
from app.services.food_catalog import GI_SOURCE, NUTRIENT_SOURCE
from app.services.inventory import today_in_app_tz
from app.services.meal_plans import (
    MEAL_TYPES,
    MealPlanError,
    _daily_targets_for_user,
    _glucose_payload,
    _meal_rank,
    _plan_remaining,
    _targets_payload,
)
from app.services.recipe_nutrition import GI_BAND_SOURCE, gi_band

_QUANTUM = Decimal("0.01")
_FIELDS = ("kcal", "carb_g", "protein_g", "fat_g", "fiber_g", "sodium_mg")
_CARB_KCAL = Decimal(4)
_PROTEIN_KCAL = Decimal(4)
_FAT_KCAL = Decimal(9)


def food_detail(session: Session, food_id: int) -> dict[str, object]:
    food = get_food(session, food_id)
    if food is None:
        raise MealPlanError(status_code=404, detail="找不到这种食材", code="food_not_found")
    conversions = session.scalars(
        select(FoodUnitConversion).where(FoodUnitConversion.food_id == food_id)
    ).all()
    units = sorted(
        {conv.unit: float(conv.grams_per_unit) for conv in conversions}.items(),
        key=lambda item: (item[0] != "克", item[0]),
    )
    band, label = gi_band(food.gi)
    return {
        "id": food.id,
        "name": food.name,
        "category": food.category,
        "per_g": float(food.per_g or Decimal(100)),
        "kcal": _num(food.kcal),
        "carb_g": _num(food.carb_g),
        "protein_g": _num(food.protein_g),
        "fat_g": _num(food.fat_g),
        "fiber_g": _num(food.fiber_g),
        "sodium_mg": _num(food.sodium_mg),
        "gi": _num(food.gi),
        "gi_band_label": label,
        "gi_band_source": GI_BAND_SOURCE,
        "gi_source": food.gi_source,
        "nutrient_source": food.nutrient_source,
        "units": [{"unit": unit, "grams_per_unit": grams} for unit, grams in units],
    }


def add_food_item(
    session: Session,
    user_id: int,
    food_id: int,
    meal_type: str,
    quantity: Decimal,
    unit: str,
    plan_date: date | None = None,
) -> tuple[MealFoodItem, bool]:
    if meal_type not in MEAL_TYPES:
        raise MealPlanError(status_code=422, detail="餐次不正确", code="invalid_meal_type")
    food = get_food(session, food_id)
    if food is None:
        raise MealPlanError(status_code=404, detail="找不到这种食材", code="food_not_found")
    if get_conversion(session, food_id, unit) is None:
        raise MealPlanError(
            status_code=422,
            detail=f"没有「{unit}」的换算，请改用克或其他单位",
            code="unknown_unit",
        )
    day = plan_date or today_in_app_tz()
    existing = _find(session, user_id, day, meal_type, food_id)
    if existing is not None:
        existing.quantity = quantity
        existing.unit = unit
        session.commit()
        session.refresh(existing)
        return existing, False
    item = MealFoodItem(
        user_id=user_id,
        date=day,
        meal_type=meal_type,
        food_id=food_id,
        quantity=quantity,
        unit=unit,
    )
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = _find(session, user_id, day, meal_type, food_id)
        if existing is None:
            raise
        existing.quantity = quantity
        existing.unit = unit
        session.commit()
        session.refresh(existing)
        return existing, False
    session.refresh(item)
    return item, True


def add_recipe_items(
    session: Session,
    user_id: int,
    recipe_id: int,
    meal_type: str,
) -> dict[str, object]:
    """把食谱拆成食材，一次性加入自定义配餐清单。"""
    if meal_type not in MEAL_TYPES:
        raise MealPlanError(status_code=422, detail="餐次不正确", code="invalid_meal_type")
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise MealPlanError(status_code=404, detail="找不到这道食谱", code="recipe_not_found")
    ingredients = session.scalars(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
    ).all()
    added = 0
    updated = 0
    for ingredient in ingredients:
        if ingredient.amount_g is None or ingredient.amount_g <= 0:
            continue
        _item, created = add_food_item(
            session,
            user_id,
            ingredient.food_id,
            meal_type,
            ingredient.amount_g,
            "克",
        )
        if created:
            added += 1
        else:
            updated += 1
    return {"recipe_id": recipe_id, "added": added, "updated": updated}


def list_food_items(session: Session, user_id: int, day: date) -> list[dict[str, object]]:
    rows = session.execute(
        select(MealFoodItem, Food)
        .join(Food, MealFoodItem.food_id == Food.id)
        .where(MealFoodItem.user_id == user_id, MealFoodItem.date == day)
    ).all()
    ranked = sorted(rows, key=lambda row: (_meal_rank(row[0].meal_type), row[0].id))
    factors = conversions_for(session, [food.id for _item, food in ranked])
    return [
        _view(item, food, factors.get((item.food_id, item.unit)))
        for item, food in ranked
    ]


def delete_food_item(session: Session, user_id: int, item_id: int) -> None:
    item = session.get(MealFoodItem, item_id)
    if item is None or item.user_id != user_id:
        raise MealPlanError(status_code=404, detail="找不到这条食材", code="item_not_found")
    session.delete(item)
    session.commit()


def food_summary(
    session: Session,
    user_id: int,
    day: date | None = None,
) -> dict[str, object]:
    report_day = day or today_in_app_tz()
    items = list_food_items(session, user_id, report_day)
    totals, incomplete = _totals(items)
    daily, glucose = _daily_targets_for_user(session, user_id)
    return {
        "date": report_day,
        "daily_targets": _targets_payload(daily),
        "glucose": _glucose_payload(glucose),
        "consumed": {**totals, "gi_weighted": _gi_weighted(items)},
        "remaining": _plan_remaining(daily, totals),
        "items": items,
        "source": NUTRIENT_SOURCE,
        "gi_source": GI_SOURCE,
        "incomplete": incomplete,
    }


def _view(
    item: MealFoodItem,
    food: Food,
    conversion: FoodUnitConversion | None,
) -> dict[str, object]:
    grams: float | None = None
    nutrients: dict[str, float | None] = {field: None for field in _FIELDS}
    kcal_estimated = False
    if conversion is not None:
        grams_value = (item.quantity * conversion.grams_per_unit).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        grams = float(grams_value)
        per_g = food.per_g or Decimal(100)
        kcal_value, kcal_estimated = _effective_kcal(food)
        for field in _FIELDS:
            raw = kcal_value if field == "kcal" else getattr(food, field)
            nutrients[field] = _num(_scaled(raw, grams_value, per_g))
    band, label = gi_band(food.gi)
    return {
        "id": item.id,
        "food_id": item.food_id,
        "food_name": food.name,
        "category": food.category,
        "meal_type": item.meal_type,
        "quantity": _num(item.quantity) or 0.0,
        "unit": item.unit,
        "grams": grams,
        "kcal_estimated": kcal_estimated,
        "gi": _num(food.gi),
        "gi_band_label": label,
        "gi_band_source": GI_BAND_SOURCE,
        "gi_source": food.gi_source,
        "nutrient_source": food.nutrient_source,
        **nutrients,
    }


def _effective_kcal(food: Food) -> tuple[Decimal | None, bool]:
    if food.kcal is not None:
        return food.kcal, False
    carb = food.carb_g
    protein = food.protein_g
    fat = food.fat_g
    if carb is None and protein is None and fat is None:
        return None, False
    total = (
        (carb or Decimal(0)) * _CARB_KCAL
        + (protein or Decimal(0)) * _PROTEIN_KCAL
        + (fat or Decimal(0)) * _FAT_KCAL
    )
    return total.quantize(_QUANTUM, rounding=ROUND_HALF_UP), True


def _scaled(value: Decimal | None, grams: Decimal, per_g: Decimal) -> Decimal | None:
    if value is None or per_g <= 0:
        return None
    return (value * grams / per_g).quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def _totals(items: list[dict[str, object]]) -> tuple[dict[str, float | None], list[str]]:
    totals: dict[str, float | None] = {}
    incomplete: list[str] = []
    for field in _FIELDS:
        parts: list[Decimal] = []
        missing = False
        for item in items:
            value = item.get(field)
            if value is None:
                missing = True
                continue
            parts.append(Decimal(str(value)))
        totals[field] = None if not parts else float(_quantize(sum(parts, start=Decimal(0))))
        if missing and parts:
            incomplete.append(field)
    return totals, incomplete


def _gi_weighted(items: list[dict[str, object]]) -> float | None:
    weighted = Decimal(0)
    carb_total = Decimal(0)
    for item in items:
        gi = item.get("gi")
        carb = item.get("carb_g")
        if gi is None or carb is None:
            continue
        weighted += Decimal(str(gi)) * Decimal(str(carb))
        carb_total += Decimal(str(carb))
    if carb_total <= 0:
        return None
    return float(_quantize(weighted / carb_total))


def _find(
    session: Session,
    user_id: int,
    day: date,
    meal_type: str,
    food_id: int,
) -> MealFoodItem | None:
    return session.scalar(
        select(MealFoodItem).where(
            MealFoodItem.user_id == user_id,
            MealFoodItem.date == day,
            MealFoodItem.meal_type == meal_type,
            MealFoodItem.food_id == food_id,
        )
    )


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def _num(value: Decimal | None) -> float | None:
    return None if value is None else float(value)

