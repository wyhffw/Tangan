from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import HealthMetric


def upsert(
    session: Session,
    user_id: int,
    day: date,
    metric_type: str,
    value: Decimal,
) -> HealthMetric:
    row = session.scalars(
        select(HealthMetric).where(
            HealthMetric.user_id == user_id,
            HealthMetric.metric_date == day,
            HealthMetric.metric_type == metric_type,
        )
    ).one_or_none()
    if row is None:
        row = HealthMetric(
            user_id=user_id, metric_date=day, metric_type=metric_type, value=value
        )
        session.add(row)
    else:
        row.value = value
    return row


def list_between(
    session: Session, user_id: int, start: date, end: date
) -> list[HealthMetric]:
    return list(
        session.scalars(
            select(HealthMetric)
            .where(
                HealthMetric.user_id == user_id,
                HealthMetric.metric_date >= start,
                HealthMetric.metric_date <= end,
            )
            .order_by(HealthMetric.metric_date.asc(), HealthMetric.metric_type.asc())
        ).all()
    )
