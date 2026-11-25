

from datetime import date

from pydantic import BaseModel, Field


class RecipientCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class RecipientView(BaseModel):
    id: int
    email: str
    enabled: bool


class SendResult(BaseModel):
    sent: int
    recipients: list[str]
    date: date
