"""把 PostgreSQL 里的食材、食谱和人工整理的疾病关系同步到 Neo4j。

节点只写名称、类别和 pg_id。疾病关系来自 CSV，不在这里生成禁忌。
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from neo4j import Driver, GraphDatabase, RoutingControl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Food, Recipe, RecipeIngredient
from app.services.recipe_nutrition import load_cooking_oil

_ROOT = Path(__file__).resolve().parents[3]
_RELATIONS = _ROOT / "data" / "processed" / "disease_relations.csv"
_NOTES = _ROOT / "data" / "processed" / "disease_notes.csv"
_KINDS = frozenset({"RECOMMEND", "AVOID", "LIMIT", "AVOID_METHOD", "SUBSTITUTE"})
_BATCH = 400


class GraphDataError(Exception):
    """关系表无法使用。"""


class GraphUnavailable(Exception):
    """Neo4j 没有配置或连不上。"""


@dataclass(frozen=True)
class RelationRow:
    kind: str
    from_name: str
    to_name: str
    reason: str
    source: str
    max_per_day: int | None
    unit: str | None


@dataclass(frozen=True)
class DiseaseNote:
    disease: str
    note: str
    source: str


def food_properties(food: Food) -> dict[str, object]:
    return {"name": food.name, "category": food.category, "pg_id": food.id}


def recipe_properties(recipe: Recipe) -> dict[str, object]:
    return {"name": recipe.name, "pg_id": recipe.id}


def contains_row(recipe_id: int, food_id: int) -> dict[str, int]:
    return {"recipe_id": recipe_id, "food_id": food_id}


def load_relations(path: Path | None = None) -> tuple[RelationRow, ...]:
    rows: list[RelationRow] = []
    seen: set[tuple[str, str, str]] = set()
    with (path or _RELATIONS).open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = _parse_relation(raw)
            key = (row.kind, row.from_name, row.to_name)
            if key in seen:
                raise GraphDataError(f"关系重复：{row.kind} {row.from_name} -> {row.to_name}")
            seen.add(key)
            rows.append(row)
    return tuple(rows)


def load_notes(path: Path | None = None) -> tuple[DiseaseNote, ...]:
    rows: list[DiseaseNote] = []
    with (path or _NOTES).open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            disease = (raw.get("disease") or "").strip()
            note = (raw.get("note") or "").strip()
            source = (raw.get("source") or "").strip()
            if not disease or not note:
                continue
            rows.append(DiseaseNote(disease=disease, note=note, source=source))
    return tuple(rows)


def neo4j_driver() -> Driver:
    settings = get_settings()
    if not settings.neo4j_uri or not settings.neo4j_password:
        raise GraphUnavailable("Neo4j 未配置")
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        connection_timeout=5,
    )


def build_graph(session: Session, driver: Driver | None = None) -> dict[str, int]:
    own_driver = driver is None
    graph = neo4j_driver() if own_driver else driver
    assert graph is not None
    try:
        graph.verify_connectivity()
        return _sync(session, graph)
    finally:
        if own_driver:
            graph.close()


def _sync(session: Session, driver: Driver) -> dict[str, int]:
    foods = list(session.scalars(select(Food).order_by(Food.id)))
    recipes = list(session.scalars(select(Recipe).order_by(Recipe.id)))
    ingredients = list(session.scalars(select(RecipeIngredient)))
    relations = load_relations()
    food_names = {food.name for food in foods}
    _write(
        driver,
        """
        MATCH (n)
        WHERE n:Food OR n:Recipe OR n:Disease OR n:Nutrient OR n:CookingMethod
        DETACH DELETE n
        """,
    )
    for statement in (
        "CREATE CONSTRAINT food_name IF NOT EXISTS FOR (n:Food) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT food_pg IF NOT EXISTS FOR (n:Food) REQUIRE n.pg_id IS UNIQUE",
        "CREATE CONSTRAINT recipe_pg IF NOT EXISTS FOR (n:Recipe) REQUIRE n.pg_id IS UNIQUE",
        "CREATE CONSTRAINT disease_name IF NOT EXISTS FOR (n:Disease) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT nutrient_name IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (n:CookingMethod) REQUIRE n.name IS UNIQUE",
    ):
        _write(driver, statement)

    food_rows = [food_properties(food) for food in foods]
    for batch in _batches(food_rows):
        _write(
            driver,
            """
            UNWIND $rows AS row
            MERGE (food:Food {name: row.name})
            SET food.category = row.category, food.pg_id = row.pg_id
            """,
            rows=batch,
        )
    extra = _name_only_foods(relations, food_names)
    if extra:
        _write(
            driver,
            """
            UNWIND $names AS name
            MERGE (food:Food {name: name})
            """,
            names=extra,
        )
    for batch in _batches([recipe_properties(recipe) for recipe in recipes]):
        _write(
            driver,
            """
            UNWIND $rows AS row
            MERGE (recipe:Recipe {pg_id: row.pg_id})
            SET recipe.name = row.name
            """,
            rows=batch,
        )
    contains = [
        contains_row(item.recipe_id, item.food_id) for item in ingredients
    ]
    for batch in _batches(contains):
        _write(
            driver,
            """
            UNWIND $rows AS row
            MATCH (recipe:Recipe {pg_id: row.recipe_id})
            MATCH (food:Food {pg_id: row.food_id})
            MERGE (recipe)-[:CONTAINS]->(food)
            """,
            rows=batch,
        )
    methods = {name for name in load_cooking_oil() if name}
    methods.update(recipe.cooking_method for recipe in recipes if recipe.cooking_method)
    methods.update(row.to_name for row in relations if row.kind == "AVOID_METHOD")
    _write(
        driver,
        """
        UNWIND $names AS name
        MERGE (:CookingMethod {name: name})
        """,
        names=sorted(methods),
    )
    for recipe in recipes:
        if not recipe.cooking_method:
            continue
        _write(
            driver,
            """
            MATCH (recipe:Recipe {pg_id: $pg_id})
            MATCH (method:CookingMethod {name: $method})
            MERGE (recipe)-[:COOKED_BY]->(method)
            """,
            pg_id=recipe.id,
            method=recipe.cooking_method,
        )
    linked, skipped = _link_relations(driver, relations, food_names)
    return {
        "foods": len(foods) + len(extra),
        "recipes": len(recipes),
        "contains": len(contains),
        "relations": linked,
        "skipped": skipped,
    }


def _link_relations(
    driver: Driver,
    relations: tuple[RelationRow, ...],
    food_names: set[str],
) -> tuple[int, int]:
    linked = 0
    skipped = 0
    for row in relations:
        if row.kind == "RECOMMEND" and row.to_name not in food_names:
            skipped += 1
            continue
        if row.kind == "SUBSTITUTE" and (
            row.from_name not in food_names or row.to_name not in food_names
        ):
            skipped += 1
            continue
        _write_relation(driver, row)
        linked += 1
    return linked, skipped


def _write_relation(driver: Driver, row: RelationRow) -> None:
    if row.kind == "RECOMMEND":
        _write(
            driver,
            """
            MERGE (disease:Disease {name: $disease})
            MERGE (food:Food {name: $food})
            MERGE (disease)-[rel:RECOMMEND]->(food)
            SET rel.reason = $reason, rel.source = $source
            """,
            disease=row.from_name,
            food=row.to_name,
            reason=row.reason,
            source=row.source,
        )
        return
    if row.kind == "AVOID":
        _write(
            driver,
            """
            MERGE (disease:Disease {name: $disease})
            MERGE (food:Food {name: $food})
            MERGE (disease)-[rel:AVOID]->(food)
            SET rel.reason = $reason, rel.source = $source
            """,
            disease=row.from_name,
            food=row.to_name,
            reason=row.reason,
            source=row.source,
        )
        return
    if row.kind == "LIMIT":
        _write(
            driver,
            """
            MERGE (disease:Disease {name: $disease})
            MERGE (nutrient:Nutrient {name: $nutrient})
            MERGE (disease)-[rel:LIMIT]->(nutrient)
            SET rel.reason = $reason, rel.source = $source,
                rel.max_per_day = $max_per_day, rel.unit = $unit
            """,
            disease=row.from_name,
            nutrient=row.to_name,
            reason=row.reason,
            source=row.source,
            max_per_day=row.max_per_day,
            unit=row.unit,
        )
        return
    if row.kind == "AVOID_METHOD":
        _write(
            driver,
            """
            MERGE (disease:Disease {name: $disease})
            MERGE (method:CookingMethod {name: $method})
            MERGE (disease)-[rel:AVOID_METHOD]->(method)
            SET rel.reason = $reason, rel.source = $source
            """,
            disease=row.from_name,
            method=row.to_name,
            reason=row.reason,
            source=row.source,
        )
        return
    _write(
        driver,
        """
        MATCH (left:Food {name: $left})
        MATCH (right:Food {name: $right})
        MERGE (left)-[rel:SUBSTITUTE]->(right)
        SET rel.reason = $reason, rel.source = $source
        """,
        left=row.from_name,
        right=row.to_name,
        reason=row.reason,
        source=row.source,
    )


def _name_only_foods(relations: tuple[RelationRow, ...], food_names: set[str]) -> list[str]:
    names = {
        row.to_name
        for row in relations
        if row.kind == "AVOID" and row.to_name not in food_names
    }
    return sorted(names)


def _parse_relation(raw: dict[str, str]) -> RelationRow:
    kind = (raw.get("kind") or "").strip()
    from_name = (raw.get("from_name") or "").strip()
    to_name = (raw.get("to_name") or "").strip()
    reason = (raw.get("reason") or "").strip()
    source = (raw.get("source") or "").strip()
    unit = (raw.get("unit") or "").strip() or None
    if kind not in _KINDS:
        raise GraphDataError(f"无法识别的关系：{kind}")
    if not from_name or not to_name or not reason or not source:
        raise GraphDataError(f"{kind} 缺少名称、理由或出处")
    max_per_day = _optional_int(raw.get("max_per_day") or "")
    if max_per_day is not None and unit is None:
        raise GraphDataError(f"{to_name} 写了上限但没有单位")
    if kind != "LIMIT" and max_per_day is not None:
        raise GraphDataError(f"{kind} 不填写每日上限")
    return RelationRow(kind, from_name, to_name, reason, source, max_per_day, unit)


def _optional_int(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    if not text.isdigit():
        raise GraphDataError(f"上限不是整数：{text}")
    return int(text)


def _write(driver: Driver, query: str, **parameters: object) -> None:
    driver.execute_query(
        query,
        parameters_=parameters,
        routing_=RoutingControl.WRITE,
    )


def _batches(rows: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    return [rows[index : index + _BATCH] for index in range(0, len(rows), _BATCH)]
