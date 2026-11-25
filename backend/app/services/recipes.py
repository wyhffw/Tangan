"""食谱详情。营养由后端按克数计算，图谱连不上时页面仍然能打开。"""

from decimal import Decimal

from neo4j.exceptions import Neo4jError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.queries import food_relations
from app.graph.sync import GraphUnavailable, neo4j_driver
from app.models.entities import Food, Recipe, RecipeIngredient
from app.services.recipe_nutrition import (
    IngredientLine,
    OilNutrients,
    RecipeNutrition,
    calculate_recipe_nutrition,
    is_cooking_oil,
    load_cooking_oil,
)


class RecipeError(Exception):
    def __init__(self, *, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def recipe_nutrition(session: Session, recipe: Recipe) -> RecipeNutrition:
    lines, _ingredients = _ingredient_lines(session, recipe)
    return _nutrition_from_lines(session, recipe, lines)


def get_recipe_detail(session: Session, recipe_id: int) -> dict[str, object]:
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise RecipeError(status_code=404, detail="找不到这道食谱", code="recipe_not_found")
    lines, ingredients = _ingredient_lines(session, recipe)
    nutrition = _nutrition_from_lines(session, recipe, lines)
    graph, links = _graph_links([item.name for item in lines])
    return {
        "id": recipe.id,
        "name": recipe.name,
        "cuisine": recipe.cuisine,
        "meal_types": list(recipe.meal_types or []),
        "cooking_method": recipe.cooking_method,
        "steps": recipe.steps,
        "servings": float(recipe.servings or Decimal(1)),
        "image_url": recipe.image_url,
        "source": recipe.source,
        "ingredients": ingredients,
        "graph": graph,
        "links": links,
        "kcal": _number(nutrition.kcal),
        "carb_g": _number(nutrition.carb_g),
        "protein_g": _number(nutrition.protein_g),
        "fat_g": _number(nutrition.fat_g),
        "fiber_g": _number(nutrition.fiber_g),
        "sodium_mg": _number(nutrition.sodium_mg),
        "oil_estimated": nutrition.oil_estimated,
        "main_staple_gi": _number(nutrition.main_staple_gi),
        "gi_band": nutrition.gi_band,
        "gi_band_label": nutrition.gi_band_label,
        "gi_band_source": nutrition.gi_band_source,
        "gl_estimate": _number(nutrition.gl_estimate),
        "gl_is_approximate": nutrition.gl_is_approximate,
    }


def _nutrition_from_lines(
    session: Session, recipe: Recipe, lines: list[IngredientLine]
) -> RecipeNutrition:
    oil = session.scalar(select(Food).where(Food.name == "花生油"))
    return calculate_recipe_nutrition(
        lines,
        servings=recipe.servings or Decimal(1),
        cooking_method=recipe.cooking_method,
        oil_table=load_cooking_oil(),
        default_oil=None
        if oil is None
        else OilNutrients(per_g=oil.per_g, kcal=oil.kcal, fat_g=oil.fat_g),
    )


def _ingredient_lines(
    session: Session, recipe: Recipe
) -> tuple[list[IngredientLine], list[dict[str, object]]]:
    rows = list(
        session.scalars(
            select(RecipeIngredient)
            .where(RecipeIngredient.recipe_id == recipe.id)
            .order_by(RecipeIngredient.id)
        )
    )
    foods = _foods(session, [row.food_id for row in rows])
    lines: list[IngredientLine] = []
    ingredients: list[dict[str, object]] = []
    for row in rows:
        food = foods.get(row.food_id)
        if food is None:
            continue
        lines.append(_line(food, row))
        ingredients.append(
            {
                "food_id": food.id,
                "name": food.name,
                "amount_g": float(row.amount_g),
                "is_main": row.is_main,
            }
        )
    return lines, ingredients


def _foods(session: Session, food_ids: list[int]) -> dict[int, Food]:
    if not food_ids:
        return {}
    rows = session.scalars(select(Food).where(Food.id.in_(food_ids)))
    return {food.id: food for food in rows}


def _line(food: Food, row: RecipeIngredient) -> IngredientLine:
    return IngredientLine(
        food_id=food.id,
        name=food.name,
        amount_g=row.amount_g,
        per_g=food.per_g or Decimal(100),
        is_main=row.is_main,
        is_oil=is_cooking_oil(food.category),
        kcal=food.kcal,
        carb_g=food.carb_g,
        protein_g=food.protein_g,
        fat_g=food.fat_g,
        fiber_g=food.fiber_g,
        sodium_mg=food.sodium_mg,
        gi=food.gi,
        gi_source=food.gi_source,
    )


def _graph_links(names: list[str]) -> tuple[str, list[dict[str, object]]]:
    try:
        driver = neo4j_driver()
    except (OSError, GraphUnavailable, Neo4jError):
        return "down", []
    try:
        links: list[dict[str, object]] = []
        for name in names:
            for link in food_relations(driver, name):
                links.append(
                    {
                        "food_name": name,
                        "relation": link.relation,
                        "direction": link.direction,
                        "other_label": link.other_label,
                        "other_name": link.other_name,
                        "reason": link.reason,
                        "source": link.source,
                    }
                )
        return "up", links
    except (OSError, GraphUnavailable, Neo4jError):
        return "down", []
    finally:
        driver.close()


def _number(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def list_recipes(
    session: Session,
    q: str | None = None,
    meal_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    """菜谱库列表。按名称子串和餐次过滤，营养数字由后端计算。"""
    recipes = list(session.scalars(select(Recipe).order_by(Recipe.id)))
    needle = (q or "").strip()
    if needle:
        recipes = [recipe for recipe in recipes if needle in recipe.name]
    if meal_type:
        recipes = [
            recipe for recipe in recipes if meal_type in (recipe.meal_types or [])
        ]
    total = len(recipes)
    start = max(0, (page - 1) * page_size)
    window = recipes[start : start + page_size]
    items: list[dict[str, object]] = []
    for recipe in window:
        nutrition = recipe_nutrition(session, recipe)
        items.append(
            {
                "id": recipe.id,
                "name": recipe.name,
                "cuisine": recipe.cuisine,
                "meal_types": list(recipe.meal_types or []),
                "cooking_method": recipe.cooking_method,
                "servings": float(recipe.servings or Decimal(1)),
                "image_url": recipe.image_url,
                "kcal": _number(nutrition.kcal),
                "carb_g": _number(nutrition.carb_g),
                "protein_g": _number(nutrition.protein_g),
                "fat_g": _number(nutrition.fat_g),
                "gi_band_label": nutrition.gi_band_label,
            }
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
