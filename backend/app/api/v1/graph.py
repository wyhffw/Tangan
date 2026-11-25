"""图谱邻居和食材营养。营养数字只在点击食材后从 PostgreSQL 返回。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.entities import User
from app.schemas.graph import DiseaseGuidanceView, FoodFacts, Neighborhood
from app.services.graph import read_disease_guidance, read_food_facts, read_neighbors

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/neighbors", response_model=Neighborhood)
def neighbors(
    _user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Query(max_length=64)] = "",
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
) -> Neighborhood:
    return Neighborhood.model_validate(read_neighbors(name, depth))


@router.get("/foods/{pg_id}", response_model=FoodFacts)
def food_facts(
    pg_id: int,
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> FoodFacts:
    return FoodFacts.model_validate(read_food_facts(session, pg_id))


@router.get("/guidance", response_model=DiseaseGuidanceView)
def guidance(
    _user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Query(max_length=64)] = "",
) -> DiseaseGuidanceView:
    return DiseaseGuidanceView.model_validate(read_disease_guidance(name))
