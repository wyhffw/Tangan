from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ChatMessage, ChatSession, PendingProfileUpdate


def get_session_for_user(
    session: Session, session_id: int, user_id: int
) -> ChatSession | None:
    row = session.get(ChatSession, session_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def list_sessions(session: Session, user_id: int) -> list[ChatSession]:
    return list(
        session.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.id.desc())
        )
    )


def list_messages(session: Session, session_id: int) -> list[ChatMessage]:
    return list(
        session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        )
    )


def add_session(session: Session, user_id: int) -> ChatSession:
    row = ChatSession(user_id=user_id)
    session.add(row)
    session.flush()
    return row


def add_message(
    session: Session,
    session_id: int,
    role: str,
    content: str,
    meta: dict[str, object] | None = None,
) -> ChatMessage:
    row = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        meta=meta or {},
    )
    session.add(row)
    session.flush()
    return row


def add_pending(
    session: Session, user_id: int, session_id: int, draft: dict[str, object]
) -> PendingProfileUpdate:
    row = PendingProfileUpdate(
        user_id=user_id,
        session_id=str(session_id),
        draft=draft,
    )
    session.add(row)
    session.flush()
    return row


def get_latest_pending(
    session: Session, user_id: int
) -> PendingProfileUpdate | None:
    return session.scalars(
        select(PendingProfileUpdate)
        .where(PendingProfileUpdate.user_id == user_id)
        .order_by(PendingProfileUpdate.id.desc())
    ).first()


def delete_pending(session: Session, pending: PendingProfileUpdate) -> None:
    session.delete(pending)
