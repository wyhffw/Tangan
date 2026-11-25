"""补充常用食材的可数单位换算与糖类营养。整表数据不进入 Git。

单位换算克数为常见食物份量参照（近似值，待核对）；糖类营养为成分表补充值（待核对）。
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.models.entities import Food, FoodUnitConversion

SUGAR_SOURCE = "《中国食物成分表》标准版第6版糖类补充值；未对照纸质书"

# 可数单位换算克数（近似，待核对）
OIL_UNITS = [("汤匙", "10"), ("茶匙", "5")]
SUGAR_UNITS = [("汤匙", "10"), ("茶匙", "5")]
SALT_UNITS = [("小勺", "5")]

# 蛋类按名字区分：蛋白约 30g，蛋黄约 20g，整蛋约 50g
EGG_UNIT = "颗"

# 糖类营养补充（kcal/100g、碳水、蛋白质、脂肪，近似待核对）
SUGAR_NUTRIENTS = {
    "绵白糖": ("396", "98.9", "0", "0"),
    "蔗糖": ("400", "99.9", "0", "0"),
    "葡萄糖": ("400", "99.5", "0", "0"),
    "果糖": ("400", "99.9", "0", "0"),
    "乳糖": ("400", "99.8", "0", "0"),
    "麦芽糖": ("400", "99.9", "0", "0"),
    "方糖": ("400", "99.9", "0", "0"),
    "蜂蜜": ("321", "75.6", "0.4", "1.9"),
}


def _egg_grams(name: str) -> str:
    if "蛋黄" in name:
        return "20"
    if "蛋白" in name:
        return "30"
    return "50"


def _add_unit(session: Session, food: Food, unit: str, grams: str) -> bool:
    existing = session.scalars(
        select(FoodUnitConversion).where(
            FoodUnitConversion.food_id == food.id,
            FoodUnitConversion.unit == unit,
        )
    ).one_or_none()
    if existing is not None:
        return False
    session.add(
        FoodUnitConversion(food_id=food.id, unit=unit, grams_per_unit=Decimal(grams))
    )
    return True


def seed(session: Session) -> dict[str, int]:
    added_units = 0
    patched_sugar = 0
    foods = session.scalars(select(Food)).all()
    for food in foods:
        category = food.category or ""
        if category == "植物油-植物油" or category == "动物油脂类-动物油脂":
            for unit, grams in OIL_UNITS:
                if _add_unit(session, food, unit, grams):
                    added_units += 1
        elif category == "糖类":
            for unit, grams in SUGAR_UNITS:
                if _add_unit(session, food, unit, grams):
                    added_units += 1
        elif category == "蛋类及其制品-鸡蛋":
            if "粉" in (food.name or ""):
                continue
            if _add_unit(session, food, EGG_UNIT, _egg_grams(food.name)):
                added_units += 1
        elif food.name == "食盐":
            for unit, grams in SALT_UNITS:
                if _add_unit(session, food, unit, grams):
                    added_units += 1
    for name, values in SUGAR_NUTRIENTS.items():
        food = session.scalars(
            select(Food).where(Food.name == name)
        ).one_or_none()
        if food is None or food.kcal is not None:
            continue
        food.kcal = Decimal(values[0])
        food.carb_g = Decimal(values[1])
        food.protein_g = Decimal(values[2])
        food.fat_g = Decimal(values[3])
        food.nutrient_source = SUGAR_SOURCE
        patched_sugar += 1
    session.commit()
    return {"units_added": added_units, "sugar_patched": patched_sugar}


def main() -> None:
    with get_sessionmaker()() as session:
        stats = seed(session)
    print(f"units_added={stats['units_added']} sugar_patched={stats['sugar_patched']}")


if __name__ == "__main__":
    main()

