"""自定义配餐：自选食材与份量的请求、响应。营养数字由后端按成分表计算。"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.recommend import DailyTargets, GlucoseStatus, RemainingBudget


class FoodUnitOption(BaseModel):
    unit: str
    grams_per_unit: float


class FoodDetail(BaseModel):
    id: int
    name: str
    category: str | None
    per_g: float
    kcal: float | None
    carb_g: float | None
    protein_g: float | None
    fat_g: float | None
    fiber_g: float | None
    sodium_mg: float | None
    gi: float | None
    gi_band_label: str | None
    gi_band_source: str
    gi_source: str | None
    nutrient_source: str | None
    units: list[FoodUnitOption]


class MealFoodCreate(BaseModel):
    food_id: int
    meal_type: str = Field(max_length=16)
    quantity: Decimal = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=32)


class RecipeFoodCreate(BaseModel):
    recipe_id: int
    meal_type: str = Field(max_length=16)


class RecipeFoodView(BaseModel):
    recipe_id: int
    added: int
    updated: int


class MealFoodItemView(BaseModel):
    id: int
    food_id: int
    food_name: str
    category: str | None
    meal_type: str
    quantity: float
    unit: str
    grams: float | None
    kcal: float | None
    kcal_estimated: bool
    carb_g: float | None
    protein_g: float | None
    fat_g: float | None
    fiber_g: float | None
    sodium_mg: float | None
    gi: float | None
    gi_band_label: str | None
    gi_band_source: str
    gi_source: str | None
    nutrient_source: str | None


class MealFoodTotals(BaseModel):
    kcal: float | None
    carb_g: float | None
    protein_g: float | None
    fat_g: float | None
    fiber_g: float | None
    sodium_mg: float | None
    gi_weighted: float | None


class MealFoodSummary(BaseModel):
    date: date
    daily_targets: DailyTargets | None = None
    glucose: GlucoseStatus | None = None
    consumed: MealFoodTotals
    remaining: RemainingBudget | None = None
    items: list[MealFoodItemView]
    source: str
    gi_source: str
    incomplete: list[str] = Field(default_factory=list)


class MealFoodView(BaseModel):
    id: int
    date: date
    meal_type: str
    food_id: int
    already_added: bool

