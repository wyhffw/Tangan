"""图谱响应。邻居接口不包含热量、GI 或营养素含量。"""

from pydantic import BaseModel


class GraphNodeView(BaseModel):
    id: str
    name: str
    label: str
    pg_id: int | None


class GraphLinkView(BaseModel):
    source: str
    target: str
    relation: str
    reason: str | None
    citation: str | None


class Neighborhood(BaseModel):
    graph: str
    center: GraphNodeView | None
    nodes: list[GraphNodeView]
    links: list[GraphLinkView]


class FoodFacts(BaseModel):
    pg_id: int
    name: str
    category: str | None
    per_g: float | None
    kcal: float | None
    carb_g: float | None
    protein_g: float | None
    fat_g: float | None
    fiber_g: float | None
    sodium_mg: float | None
    gi: float | None
    gi_source: str
    nutrient_source: str


class DiseaseNoteView(BaseModel):
    note: str
    source: str


class GuidanceFoodView(BaseModel):
    name: str
    reason: str | None
    source: str | None


class GuidanceLimitView(BaseModel):
    name: str
    max_per_day: int | None
    unit: str | None
    reason: str | None
    source: str | None


class DiseaseGuidanceView(BaseModel):
    graph: str
    disease: str | None
    notes: list[DiseaseNoteView]
    recommended: list[GuidanceFoodView]
    avoided: list[GuidanceFoodView]
    limits: list[GuidanceLimitView]
    avoided_methods: list[GuidanceFoodView]
