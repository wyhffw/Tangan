"""每日健康指标。写入时间序列，并同步最新值到健康档案。"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.metrics import list_between, upsert
from app.repositories.profiles import get_by_user_id

METRIC_TYPES = ("weight_kg", "fasting_glucose", "hba1c")

_PROFILE_FIELDS = {
    "weight_kg": "weight_kg",
    "fasting_glucose": "fasting_glucose",
    "hba1c": "hba1c",
}


def save_daily(
    session: Session, user_id: int, day: date, values: dict[str, Decimal]
) -> dict[str, object]:
    """写入当天指标并同步到档案，返回该日指标点。"""
    for metric_type in METRIC_TYPES:
        value = values.get(metric_type)
        if value is None:
            continue
        upsert(session, user_id, day, metric_type, value)
    _sync_profile(session, user_id, values)
    session.commit()
    return {"date": day, **{t: _to_float(values.get(t)) for t in METRIC_TYPES}}


def list_points(
    session: Session, user_id: int, start: date, end: date
) -> dict[str, object]:
    rows = list_between(session, user_id, start, end)
    by_date: dict[date, dict[str, Decimal]] = {}
    for row in rows:
        by_date.setdefault(row.metric_date, {})[row.metric_type] = row.value
    points = [
        {"date": day, **{t: _to_float(values.get(t)) for t in METRIC_TYPES}}
        for day, values in sorted(by_date.items())
    ]
    return {"points": points}


def _sync_profile(session: Session, user_id: int, values: dict[str, Decimal]) -> None:
    profile = get_by_user_id(session, user_id)
    if profile is None:
        return
    changed = False
    for metric_type, field in _PROFILE_FIELDS.items():
        value = values.get(metric_type)
        if value is not None:
            setattr(profile, field, value)
            changed = True
    if changed:
        session.add(profile)


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
