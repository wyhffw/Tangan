"""从本机成分表和 GI 表导入食物。整表不进入 Git。"""

import csv
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.models.entities import Food, FoodUnitConversion
from app.services.food_catalog import (
    GI_SOURCE,
    NUTRIENT_SOURCE,
    FoodRecord,
    composition_records,
    gi_records,
)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
UNMATCHED = ROOT / "data" / "processed" / "unmatched.csv"
COMPOSITION = RAW / "food-composition-v6-fixed-en.csv"
GI_FILE = RAW / "glycemic-index-of-foods.json"

# 演示食材简名 -> 成分表规范名。能精确同名（燕麦、糙米、荞麦、小米、胡萝卜、
# 花生油）的走下方 import_foods 的 by_name 匹配，不在这里重复列。
SEED_NAME_TO_COMPOSITION = {
    "大米": "稻米（代表值）",
    "玉米": "玉米（鲜）",
    "红薯": "甘薯（红心）［山芋、红薯］",
    "番茄": "番茄［西红柿］",
    "黄瓜": "黄瓜（鲜）［胡瓜］",
    "西兰花": "西兰花［绿菜花］",
    "菠菜": "菠菜（鲜）［赤根菜］",
    "大白菜": "大白菜（代表值）",
    "香菇": "香菇（鲜）［香蕈，冬菇］",
    "芹菜": "芹菜茎",
    "鸡蛋": "鸡蛋（代表值）",
    "鸡胸肉": "鸡胸脯肉",
    "瘦猪肉": "猪肉（瘦）",
    "牛肉": "牛肉（代表值，瘦，fat3g）",
    "北豆腐": "豆腐（北豆腐）",
    "南豆腐": "豆腐（南豆腐）",
    "苹果": "苹果（代表值）",
    "梨": "梨（代表值）",
    "柚子": "柚［文旦］",
    "草莓": "草莓［洋莓，凤阳草莓］",
    "纯牛奶": "纯牛奶（代表值，全脂）",
    "无糖酸奶": "酸奶（代表值，全脂）",
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _gi_groups() -> list[dict[str, object]]:
    payload = json.loads(
        GI_FILE.read_text(encoding="utf-8"), parse_float=Decimal, parse_int=Decimal
    )
    if not isinstance(payload, list):
        raise TypeError("GI 文件不是列表")
    return payload


def _ensure_gram(session: Session, food: Food) -> None:
    existing = session.scalars(
        select(FoodUnitConversion).where(
            FoodUnitConversion.food_id == food.id,
            FoodUnitConversion.unit == "克",
        )
    ).one_or_none()
    if existing is None:
        session.add(
            FoodUnitConversion(food_id=food.id, unit="克", grams_per_unit=Decimal(1))
        )


def write_unmatched(rows: list[tuple[str, str, str]]) -> None:
    UNMATCHED.parent.mkdir(parents=True, exist_ok=True)
    with UNMATCHED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kind", "name", "detail"])
        writer.writerows(rows)


def _apply_record(food: Food, record: FoodRecord) -> None:
    """把成分表记录写进食物（food_code、别名、营养），不改 name。"""
    food.food_code = record.food_code
    food.category = record.category or food.category
    food.alias = sorted({*(food.alias or []), *record.alias})
    food.kcal = record.kcal
    food.carb_g = record.carb_g
    food.protein_g = record.protein_g
    food.fat_g = record.fat_g
    food.fiber_g = record.fiber_g
    food.sodium_mg = record.sodium_mg
    food.nutrient_source = NUTRIENT_SOURCE
    food.per_g = Decimal(100)


def _merge_seed_foods(
    by_name: dict[str, Food],
    by_code: dict[str, Food],
    composition_by_name: dict[str, FoodRecord],
) -> set[str]:
    """让演示食材简名食物直接承载成分表数据，不新建重复的规范名食物。

    演示食材用简名（如「番茄」），成分表用规范名（如「番茄［西红柿］」）。
    把规范名的 food_code、别名和营养并进简名食物，name 保留简名；返回这些
    规范名集合，供 upsert 阶段跳过，避免再插入一条重复记录。
    """
    merged: set[str] = set()
    for seed_name, comp_name in SEED_NAME_TO_COMPOSITION.items():
        food = by_name.get(seed_name)
        record = composition_by_name.get(comp_name)
        if food is None or record is None:
            continue
        _apply_record(food, record)
        by_code[record.food_code] = food
        by_name[comp_name] = food
        merged.add(comp_name)
    return merged


def import_foods(session: Session) -> dict[str, int]:
    by_code: dict[str, Food] = {}
    by_name: dict[str, Food] = {}
    for food in session.scalars(select(Food)):
        by_name[food.name] = food
        if food.food_code:
            by_code[food.food_code] = food

    records = composition_records(_rows(COMPOSITION))
    composition_by_name = {record.name: record for record in records}
    merged = _merge_seed_foods(by_name, by_code, composition_by_name)

    upserted = 0
    for record in records:
        if record.name in merged:
            continue  # 已并进演示食材简名食物，不再插入规范名副本
        food = by_code.get(record.food_code) or by_name.get(record.name)
        if food is None:
            food = Food(name=record.name, alias=[], per_g=Decimal(100))
            session.add(food)
        elif food.name != record.name:
            by_name.pop(food.name, None)
        food.name = record.name
        _apply_record(food, record)
        by_code[record.food_code] = food
        by_name[record.name] = food
        upserted += 1
    session.flush()
    for food in by_code.values():
        _ensure_gram(session, food)

    ready, conflicts = gi_records(_gi_groups())
    attached = 0
    inserted = 0
    unmatched = [("gi_conflict", name, detail) for name, detail in conflicts]
    for record in ready:
        food = by_name.get(record.name)
        if food is None:
            food = Food(
                name=record.name,
                alias=[],
                category=record.category,
                gi=record.gi,
                gi_source=GI_SOURCE,
                per_g=Decimal(100),
            )
            session.add(food)
            by_name[record.name] = food
            inserted += 1
            unmatched.append(
                ("gi_not_in_composition", record.name, "成分表无同名食物，营养素留空")
            )
        else:
            food.gi = record.gi
            food.gi_source = GI_SOURCE
            attached += 1
        session.flush()
        _ensure_gram(session, food)
    write_unmatched(unmatched)
    return {"foods": upserted, "gi_attached": attached, "gi_inserted": inserted}


def main() -> None:
    if not COMPOSITION.exists() or not GI_FILE.exists():
        raise SystemExit("缺少 data/raw 中的成分表或 GI 文件")
    with get_sessionmaker()() as session:
        stats = import_foods(session)
        session.commit()
    print(
        f"foods={stats['foods']} gi_attached={stats['gi_attached']} gi_only={stats['gi_inserted']}"
    )


if __name__ == "__main__":
    main()
