from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_audit
from app.db.session import get_session
from app.models.entities import User
from app.schemas.metrics import MetricList, MetricPoint, MetricWrite
from app.services.metrics import list_points, save_daily

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricList)
def read_metrics(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> MetricList:
    today = date.today()
    end_day = end or today
    start_day = start or (end_day - timedelta(days=29))
    if start_day > end_day:
        raise HTTPException(status_code=422, detail="start 不能晚于 end")
    return MetricList.model_validate(list_points(session, user.id, start_day, end_day))


@router.post("", response_model=MetricPoint)
def post_metrics(
    body: MetricWrite,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> MetricPoint:
    saved = save_daily(session, user.id, body.date, body.metrics())
    record_audit(
        action="metrics.upsert",
        target=f"user:{user.id}",
        request_id=request.state.request_id,
        actor_id=str(user.id),
    )
    return MetricPoint.model_validate(saved)
