"""加入今日计划。日期由服务器按 Asia/Shanghai 填写。"""

from datetime import date

from pydantic import BaseModel, Field
from app.schemas.recommend import DailyTargets, GlucoseStatus, RemainingBudget
from app.schemas.reports import NutrientTotals, ReportItem


class MealPlanCreate(BaseModel):
    recipe_id: int
    meal_type: str = Field(max_length=16)


class MealPlanItem(BaseModel):
    id: int
    date: date
    meal_type: str
    recipe_id: int
    recipe_name: str
    servings: float


class MealPlanView(BaseModel):
    id: int
    date: date
    meal_type: str
    recipe_id: int
    already_added: bool


class PlanSummary(BaseModel):
    date: date
    daily_targets: DailyTargets | None = None
    glucose: GlucoseStatus | None = None
    consumed: NutrientTotals
    remaining: RemainingBudget | None = None
    items: list[ReportItem]
