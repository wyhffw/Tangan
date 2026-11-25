from decimal import Decimal
from unittest.mock import MagicMock

from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
from app.models.entities import Food, FoodUnitConversion, HealthProfile, MealPlan
from app.repositories.foods import find_food_by_name

EXPECTED_TABLES = {
    "users",
    "health_profiles",
    "health_metrics",
    "pending_profile_updates",
    "foods",
    "food_unit_conversions",
    "recipes",
    "recipe_ingredients",
    "inventory_items",
    "meal_plans",
    "meal_food_items",
    "shopping_lists",
    "shopping_items",
    "chat_sessions",
    "chat_messages",
    "recommend_logs",
    "report_recipients",
    "audit_logs",
}


def test_metadata_lists_every_planned_table() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_json_fields_use_postgres_jsonb() -> None:
    assert isinstance(HealthProfile.__table__.c.diseases.type, JSONB)
    assert isinstance(HealthProfile.__table__.c.allergies.type, JSONB)
    assert isinstance(HealthProfile.__table__.c.dislikes.type, JSONB)
    assert isinstance(HealthProfile.__table__.c.preferences.type, JSONB)
    assert isinstance(Food.__table__.c.alias.type, JSONB)
    assert Food.__table__.c.per_g.server_default is not None


def test_meal_plan_and_unit_conversion_are_unique() -> None:
    meal_names = {constraint.name for constraint in MealPlan.__table__.constraints}
    unit_names = {
        constraint.name for constraint in FoodUnitConversion.__table__.constraints
    }
    assert "uq_meal_plan_slot" in meal_names
    assert "uq_food_unit" in unit_names


def test_find_food_by_name_asks_the_session() -> None:
    food = Food(name="测试食材", per_g=Decimal(100))
    session = MagicMock()
    session.scalars.return_value.one_or_none.return_value = food

    found = find_food_by_name(session, "测试食材")

    assert found is food
    statement = session.scalars.call_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "foods" in compiled
    assert "测试食材" in compiled
