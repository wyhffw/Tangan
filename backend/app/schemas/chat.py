from typing import Any, Literal

from pydantic import BaseModel, Field

Route = Literal["knowledge", "recommend", "report", "profile_update", "help", "blocked"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


class ChatSource(BaseModel):
    chunk_id: str
    source: str
    page: int


class ChatReply(BaseModel):
    session_id: int
    route: Route
    blocked: bool
    answer: str
    citation_ids: list[str]
    sources: list[ChatSource]
    graph: str
    rag: str
    pending_profile_id: int | None = None
    draft: dict[str, Any] = Field(default_factory=dict)


class ChatSessionSummary(BaseModel):
    id: int
    preview: str


class ChatMessageView(BaseModel):
    id: int
    role: str
    content: str
    meta: dict[str, Any]


class ChatSessionDetail(BaseModel):
    id: int
    messages: list[ChatMessageView]
