"""食谱详情。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.entities import User
from app.schemas.recipes import RecipeDetail, RecipeList
from app.services.recipes import get_recipe_detail, list_recipes

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeList)
def read_recipes(
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    q: Annotated[str | None, Query()] = None,
    meal_type: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RecipeList:
    return RecipeList.model_validate(
        list_recipes(session, q=q, meal_type=meal_type, page=page, page_size=page_size)
    )


@router.get("/{recipe_id}", response_model=RecipeDetail)
def read_recipe(
    recipe_id: int,
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RecipeDetail:
    return RecipeDetail.model_validate(get_recipe_detail(session, recipe_id))
