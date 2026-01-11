from datetime import datetime
from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    value: float
    category: str = Field(min_length=1, max_length=64)
    timestamp: datetime | None = None


class RecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    value: float | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    timestamp: datetime | None = None


class RecordOut(BaseModel):
    id: int
    title: str
    value: float
    category: str
    timestamp: datetime
    is_anomaly: bool
    created_by: int


class PaginatedRecords(BaseModel):
    items: list[RecordOut]
    page: int
    size: int
    total: int
