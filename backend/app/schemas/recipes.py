"""食谱详情。营养字段与推荐结果相同，由后端填写。"""

from pydantic import BaseModel


class RecipeIngredientView(BaseModel):
    food_id: int
    name: str
    amount_g: float
    is_main: bool


class RecipeGraphLink(BaseModel):
    food_name: str
    relation: str
    direction: str
    other_label: str
    other_name: str
    reason: str | None
    source: str | None


class RecipeDetail(BaseModel):
    id: int
    name: str
    cuisine: str | None
    meal_types: list[str]
    cooking_method: str | None
    steps: str | None
    servings: float
    image_url: str | None
    source: str | None
    ingredients: list[RecipeIngredientView]
    graph: str
    links: list[RecipeGraphLink]
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


class RecipeSummary(BaseModel):
    id: int
    name: str
    cuisine: str | None
    meal_types: list[str]
    cooking_method: str | None
    servings: float
    image_url: str | None
    kcal: float | None
    carb_g: float | None
    protein_g: float | None
    fat_g: float | None
    gi_band_label: str | None


class RecipeList(BaseModel):
    items: list[RecipeSummary]
    total: int
    page: int
    page_size: int
