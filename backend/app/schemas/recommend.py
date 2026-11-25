"""推荐接口的请求和响应。营养数字由后端填写。"""

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    meal_type: str | None = Field(default=None, max_length=16)
    only_inventory: bool = False
    exclude_ids: list[int] = Field(default_factory=list)


class RecommendItem(BaseModel):
    recipe_id: int
    name: str
    score: int
    reason: str
    citation_ids: list[str]
    missing_foods: list[str]
    held_foods: list[str]
    kcal: float | None
    carb_g: float | None
    protein_g: float | None
    fat_g: float | None
    fiber_g: float | None
    sodium_mg: float | None
    oil_estimated: bool
    main_staple_gi: float | None
    gi_band: str | None
    gi_band_label: str | None
    gi_band_source: str
    gl_estimate: float | None
    gl_is_approximate: bool
    carb_servings: float | None = None


class RejectReason(BaseModel):
    rule_id: str
    message: str
    source: str


class RejectedRecipe(BaseModel):
    recipe_id: int
    name: str
    reasons: list[RejectReason]


class DailyTargets(BaseModel):
    daily_kcal: int
    carb_g: float
    protein_g: float
    fat_g: float
    macro_source: str
    meal_split_source: str


class MealTargets(BaseModel):
    meal_type: str
    kcal: float
    carb_g: float
    protein_g: float
    fat_g: float


class GlucoseStatus(BaseModel):
    level: str
    fasting_glucose: float | None
    hba1c: float | None
    carb_scale: float
    source: str


class ConsumedItem(BaseModel):
    recipe_id: int
    name: str
    meal_type: str
    kcal: float | None
    carb_g: float | None
    protein_g: float | None = None
    fat_g: float | None = None


class Consumed(BaseModel):
    items: list[ConsumedItem]
    kcal: float | None
    carb_g: float | None
    protein_g: float | None = None
    fat_g: float | None = None


class RemainingBudget(BaseModel):
    kcal: float
    carb_g: float
    protein_g: float
    fat_g: float


class RecommendResponse(BaseModel):
    graph: str
    rag: str
    blocked: bool
    block_message: str | None
    strict: list[RecommendItem]
    relaxed: list[RecommendItem]
    rejected: list[RejectedRecipe]
    daily_targets: DailyTargets | None = None
    meal_targets: MealTargets | None = None
    glucose: GlucoseStatus | None = None
    consumed: Consumed | None = None
    remaining: RemainingBudget | None = None
