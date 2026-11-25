

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.entities import User
from app.schemas.report_delivery import RecipientCreate, RecipientView, SendResult
from app.services.report_delivery import (
    add_recipient,
    delete_recipient,
    list_recipients,
    send_daily,
)

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/recipients", response_model=list[RecipientView])
def read_recipients(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[RecipientView]:
    return [
        RecipientView(id=item.id, email=item.email, enabled=item.enabled)
        for item in list_recipients(session, user.id)
    ]


@router.post("/recipients", response_model=RecipientView)
def create_recipient(
    body: RecipientCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RecipientView:
    recipient = add_recipient(session, user.id, body.email)
    return RecipientView(id=recipient.id, email=recipient.email, enabled=recipient.enabled)


@router.delete("/recipients/{recipient_id}")
def remove_recipient(
    recipient_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, bool]:
    delete_recipient(session, user.id, recipient_id)
    return {"ok": True}


@router.post("/send", response_model=SendResult)
def send_report(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    day: Annotated[date | None, Query(alias="date")] = None,
) -> SendResult:
    result = send_daily(session, user.id, day)
    return SendResult.model_validate(result)
