"""把食谱加入今日计划。同一天、同一餐、同一道菜只保留一条。"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import MealPlan, Recipe
from app.services.inventory import today_in_app_tz
from app.repositories.metrics import list_between
from app.repositories.profiles import get_by_user_id
from app.services.daily_targets import (
    DailyTargets,
    GlucoseStatus,
    daily_targets,
    glucose_status,
)

MEAL_TYPES = ("早餐", "午餐", "晚餐", "加餐")


class MealPlanError(Exception):
    def __init__(self, *, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def add_to_plan(
    session: Session,
    user_id: int,
    recipe_id: int,
    meal_type: str,
    plan_date: date | None = None,
) -> tuple[MealPlan, bool]:
    if meal_type not in MEAL_TYPES:
        raise MealPlanError(status_code=422, detail="餐次不正确", code="invalid_meal_type")
    if session.get(Recipe, recipe_id) is None:
        raise MealPlanError(status_code=404, detail="找不到这道食谱", code="recipe_not_found")
    day = plan_date or today_in_app_tz()
    existing = _find(session, user_id, day, meal_type, recipe_id)
    if existing is not None:
        return existing, False
    plan = MealPlan(
        user_id=user_id,
        date=day,
        meal_type=meal_type,
        recipe_id=recipe_id,
        servings=Decimal(1),
    )
    session.add(plan)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = _find(session, user_id, day, meal_type, recipe_id)
        if existing is None:
            raise
        return existing, False
    session.refresh(plan)
    return plan, True


def list_plans(session: Session, user_id: int, day: date) -> list[dict[str, object]]:
    rows = session.execute(
        select(MealPlan, Recipe)
        .join(Recipe, MealPlan.recipe_id == Recipe.id)
        .where(MealPlan.user_id == user_id, MealPlan.date == day)
    ).all()
    ranked = sorted(rows, key=lambda row: (_meal_rank(row[0].meal_type), row[0].id))
    return [
        {
            "id": plan.id,
            "date": plan.date,
            "meal_type": plan.meal_type,
            "recipe_id": plan.recipe_id,
            "recipe_name": recipe.name,
            "servings": float(plan.servings),
        }
        for plan, recipe in ranked
    ]


def delete_plan(session: Session, user_id: int, plan_id: int) -> None:
    plan = session.get(MealPlan, plan_id)
    if plan is None or plan.user_id != user_id:
        raise MealPlanError(status_code=404, detail="找不到这条计划", code="plan_not_found")
    session.delete(plan)
    session.commit()


def _meal_rank(meal_type: str) -> int:
    try:
        return MEAL_TYPES.index(meal_type)
    except ValueError:
        return len(MEAL_TYPES)


def _find(
    session: Session,
    user_id: int,
    day: date,
    meal_type: str,
    recipe_id: int,
) -> MealPlan | None:
    return session.scalar(
        select(MealPlan).where(
            MealPlan.user_id == user_id,
            MealPlan.date == day,
            MealPlan.meal_type == meal_type,
            MealPlan.recipe_id == recipe_id,
        )
    )


def plan_summary(
    session: Session,
    user_id: int,
    day: date | None = None,
) -> dict[str, object]:
    """自建清单的营养汇总：目标、已摄入、剩余与逐条明细。"""
    from app.services.reports import daily_report

    report_day = day or today_in_app_tz()
    report = daily_report(session, user_id, report_day)
    daily, glucose = _daily_targets_for_user(session, user_id)
    return {
        "date": report_day,
        "daily_targets": _targets_payload(daily),
        "glucose": _glucose_payload(glucose),
        "consumed": report["totals"],
        "remaining": _plan_remaining(daily, report["totals"]),
        "items": report["items"],
    }


def _daily_targets_for_user(
    session: Session,
    user_id: int,
) -> tuple[DailyTargets | None, GlucoseStatus | None]:
    profile = get_by_user_id(session, user_id)
    if profile is None:
        return None, None
    metrics = _today_metrics(session, user_id)
    weight = (
        metrics["weight_kg"] if metrics["weight_kg"] is not None else profile.weight_kg
    )
    fasting = (
        metrics["fasting_glucose"]
        if metrics["fasting_glucose"] is not None
        else profile.fasting_glucose
    )
    hba1c = metrics["hba1c"] if metrics["hba1c"] is not None else profile.hba1c
    glucose = glucose_status(fasting, hba1c)
    daily = daily_targets(
        profile.height_cm,
        weight,
        profile.activity_level,
        carb_scale=glucose.carb_scale,
    )
    return daily, glucose


def _today_metrics(session: Session, user_id: int) -> dict[str, object]:
    today = today_in_app_tz()
    rows = list_between(session, user_id, today, today)
    values = {row.metric_type: row.value for row in rows}
    return {
        "weight_kg": values.get("weight_kg"),
        "fasting_glucose": values.get("fasting_glucose"),
        "hba1c": values.get("hba1c"),
    }


def _targets_payload(daily: DailyTargets | None) -> dict[str, object] | None:
    if daily is None:
        return None
    return {
        "daily_kcal": daily.daily_kcal,
        "carb_g": float(daily.carb_g),
        "protein_g": float(daily.protein_g),
        "fat_g": float(daily.fat_g),
        "macro_source": daily.macro_source,
        "meal_split_source": daily.meal_split_source,
    }


def _glucose_payload(glucose: GlucoseStatus | None) -> dict[str, object] | None:
    if glucose is None:
        return None
    return {
        "level": glucose.level,
        "fasting_glucose": glucose.fasting_glucose,
        "hba1c": glucose.hba1c,
        "carb_scale": float(glucose.carb_scale),
        "source": glucose.source,
    }


def _plan_remaining(
    daily: DailyTargets | None,
    totals: dict[str, object],
) -> dict[str, object] | None:
    if daily is None:
        return None
    kcal = totals.get("kcal")
    carb = totals.get("carb_g")
    protein = totals.get("protein_g")
    fat = totals.get("fat_g")
    if kcal is None or carb is None or protein is None or fat is None:
        return None
    return {
        "kcal": round(max(0.0, float(daily.daily_kcal) - float(kcal)), 2),
        "carb_g": round(max(0.0, float(daily.carb_g) - float(carb)), 2),
        "protein_g": round(max(0.0, float(daily.protein_g) - float(protein)), 2),
        "fat_g": round(max(0.0, float(daily.fat_g) - float(fat)), 2),
    }
