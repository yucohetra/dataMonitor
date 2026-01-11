from pydantic import BaseModel
from datetime import datetime


class SummaryOut(BaseModel):
    count: int
    sum: float
    avg: float
    min: float
    max: float


class CategoryAggItem(BaseModel):
    category: str
    count: int
    avg: float
    min: float
    max: float


class TrendPoint(BaseModel):
    bucket_start: datetime
    avg: float
    count: int
