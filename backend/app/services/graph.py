"""知识图谱查询。节点不带 GI 和营养数字，点击食材后再读 PostgreSQL。"""

from decimal import Decimal

from neo4j.exceptions import Neo4jError
from sqlalchemy.orm import Session

from app.graph.queries import (
    GraphNode,
    GraphQueryError,
    disease_guidance,
    neighborhood,
)
from app.graph.sync import GraphUnavailable, load_notes, neo4j_driver
from app.repositories.inventory import get_food


class GraphError(Exception):
    def __init__(self, *, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def read_neighbors(name: str, depth: int) -> dict[str, object]:
    cleaned = name.strip()
    if not cleaned:
        raise GraphError(status_code=422, detail="请输入食材或疾病", code="name_required")
    if depth not in {1, 2}:
        raise GraphError(status_code=422, detail="只能看一度或二度", code="invalid_depth")
    try:
        driver = neo4j_driver()
    except GraphUnavailable:
        return _down()
    try:
        driver.verify_connectivity()
        center, nodes, edges = neighborhood(driver, cleaned, depth)
    except (OSError, GraphUnavailable, Neo4jError, GraphQueryError):
        return _down()
    finally:
        driver.close()
    return {
        "graph": "up",
        "center": None if center is None else _node(center),
        "nodes": [_node(item) for item in nodes],
        "links": [
            {
                "source": item.source,
                "target": item.target,
                "relation": item.relation,
                "reason": item.reason,
                "citation": item.citation,
            }
            for item in edges
        ],
    }


def read_food_facts(session: Session, pg_id: int) -> dict[str, object]:
    food = get_food(session, pg_id)
    if food is None:
        raise GraphError(status_code=404, detail="成分表里没有这种食材", code="food_not_found")
    return {
        "pg_id": food.id,
        "name": food.name,
        "category": food.category,
        "per_g": _number(food.per_g),
        "kcal": _number(food.kcal),
        "carb_g": _number(food.carb_g),
        "protein_g": _number(food.protein_g),
        "fat_g": _number(food.fat_g),
        "fiber_g": _number(food.fiber_g),
        "sodium_mg": _number(food.sodium_mg),
        "gi": _number(food.gi),
        "gi_source": food.gi_source or "待核对",
        "nutrient_source": food.nutrient_source or "待核对",
    }


def read_disease_guidance(name: str) -> dict[str, object]:
    """疾病饮食指导：注意事项 + 该吃 / 不该吃 / 限量 / 避免做法。"""
    cleaned = name.strip()
    if not cleaned:
        raise GraphError(status_code=422, detail="请输入疾病名称", code="name_required")
    try:
        driver = neo4j_driver()
    except GraphUnavailable:
        return _guidance_down()
    try:
        driver.verify_connectivity()
        guidance = disease_guidance(driver, cleaned)
    except (OSError, GraphUnavailable, Neo4jError, GraphQueryError):
        return _guidance_down()
    finally:
        driver.close()
    notes = [n for n in load_notes() if n.disease == cleaned]
    has_guidance = bool(
        guidance.recommended
        or guidance.avoided
        or guidance.limits
        or guidance.avoided_methods
    )
    if not has_guidance and not notes:
        return {
            "graph": "up",
            "disease": None,
            "notes": [],
            "recommended": [],
            "avoided": [],
            "limits": [],
            "avoided_methods": [],
        }
    return {
        "graph": "up",
        "disease": cleaned,
        "notes": [{"note": n.note, "source": n.source} for n in notes],
        "recommended": [
            {"name": f.name, "reason": f.reason, "source": f.source}
            for f in guidance.recommended
        ],
        "avoided": [
            {"name": f.name, "reason": f.reason, "source": f.source}
            for f in guidance.avoided
        ],
        "limits": [
            {
                "name": l.name,
                "max_per_day": l.max_per_day,
                "unit": l.unit,
                "reason": l.reason,
                "source": l.source,
            }
            for l in guidance.limits
        ],
        "avoided_methods": [
            {"name": m.name, "reason": m.reason, "source": m.source}
            for m in guidance.avoided_methods
        ],
    }


def _down() -> dict[str, object]:
    return {"graph": "down", "center": None, "nodes": [], "links": []}


def _guidance_down() -> dict[str, object]:
    return {
        "graph": "down",
        "disease": None,
        "notes": [],
        "recommended": [],
        "avoided": [],
        "limits": [],
        "avoided_methods": [],
    }


def _node(item: GraphNode) -> dict[str, object]:
    return {
        "id": item.node_id,
        "name": item.name,
        "label": item.label,
        "pg_id": item.pg_id,
    }


def _number(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
