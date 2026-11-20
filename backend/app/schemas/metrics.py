"""每日健康指标：体重、空腹血糖、糖化血红蛋白。"""

from datetime import date as CalendarDate
from decimal import Decimal

from pydantic import BaseModel, Field


class MetricWrite(BaseModel):
    date: CalendarDate
    weight_kg: Decimal | None = Field(default=None, gt=20, le=300)
    fasting_glucose: Decimal | None = Field(default=None, gt=0, le=40)
    hba1c: Decimal | None = Field(default=None, gt=0, le=30)

    def metrics(self) -> dict[str, Decimal]:
        out: dict[str, Decimal] = {}
        for name in ("weight_kg", "fasting_glucose", "hba1c"):
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        return out


class MetricPoint(BaseModel):
    date: CalendarDate
    weight_kg: float | None = None
    fasting_glucose: float | None = None
    hba1c: float | None = None


class MetricList(BaseModel):
    points: list[MetricPoint]
