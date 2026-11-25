"""今日计划。同一天同一餐同一道菜重复加入时返回原来的记录。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.entities import User
from app.schemas.meal_plans import (
    MealPlanCreate,
    MealPlanItem,
    MealPlanView,
    PlanSummary,
)
from app.services.inventory import today_in_app_tz
from app.services.meal_plans import add_to_plan, delete_plan, list_plans, plan_summary

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


@router.get("", response_model=list[MealPlanItem])
def read_meal_plans(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    day: Annotated[date | None, Query(alias="date")] = None,
) -> list[MealPlanItem]:
    report_day = day or today_in_app_tz()
    return [MealPlanItem.model_validate(item) for item in list_plans(session, user.id, report_day)]


@router.get("/summary", response_model=PlanSummary)
def read_plan_summary(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    day: Annotated[date | None, Query(alias="date")] = None,
) -> PlanSummary:
    return PlanSummary.model_validate(plan_summary(session, user.id, day))


@router.post("", response_model=MealPlanView)
def create_meal_plan(
    body: MealPlanCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> MealPlanView:
    plan, created = add_to_plan(session, user.id, body.recipe_id, body.meal_type)
    return MealPlanView(
        id=plan.id,
        date=plan.date,
        meal_type=plan.meal_type,
        recipe_id=plan.recipe_id,
        already_added=not created,
    )


@router.delete("/{plan_id}", status_code=204)
def remove_meal_plan(
    plan_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    delete_plan(session, user.id, plan_id)
    return Response(status_code=204)
