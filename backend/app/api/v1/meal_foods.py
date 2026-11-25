"""自定义配餐接口。同一天同一餐同一食材重复加入时更新份量。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.entities import User
from app.schemas.meal_foods import (
    FoodDetail,
    MealFoodCreate,
    MealFoodItemView,
    MealFoodSummary,
    MealFoodView,
    RecipeFoodCreate,
    RecipeFoodView,
)
from app.services.inventory import today_in_app_tz
from app.services.meal_foods import (
    add_food_item,
    add_recipe_items,
    delete_food_item,
    food_detail,
    food_summary,
    list_food_items,
)

router = APIRouter(prefix="/meal-foods", tags=["meal-foods"])


@router.get("/foods/{food_id}", response_model=FoodDetail)
def read_food(
    food_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> FoodDetail:
    return FoodDetail.model_validate(food_detail(session, food_id))


@router.get("", response_model=list[MealFoodItemView])
def read_items(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    day: Annotated[date | None, Query(alias="date")] = None,
) -> list[MealFoodItemView]:
    report_day = day or today_in_app_tz()
    return [MealFoodItemView.model_validate(item) for item in list_food_items(session, user.id, report_day)]


@router.get("/summary", response_model=MealFoodSummary)
def read_summary(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    day: Annotated[date | None, Query(alias="date")] = None,
) -> MealFoodSummary:
    return MealFoodSummary.model_validate(food_summary(session, user.id, day))


@router.post("", response_model=MealFoodView)
def create_item(
    body: MealFoodCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> MealFoodView:
    item, created = add_food_item(
        session, user.id, body.food_id, body.meal_type, body.quantity, body.unit
    )
    return MealFoodView(
        id=item.id,
        date=item.date,
        meal_type=item.meal_type,
        food_id=item.food_id,
        already_added=not created,
    )


@router.post("/recipe", response_model=RecipeFoodView)
def add_recipe(
    body: RecipeFoodCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RecipeFoodView:
    result = add_recipe_items(session, user.id, body.recipe_id, body.meal_type)
    return RecipeFoodView.model_validate(result)


@router.delete("/{item_id}", status_code=204)
def remove_item(
    item_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    delete_food_item(session, user.id, item_id)
    return Response(status_code=204)

