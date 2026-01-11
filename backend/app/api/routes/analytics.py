from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.schemas.analytics import SummaryOut, CategoryAggItem
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryOut)
async def summary(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    data = await AnalyticsService.summary(db, start_time, end_time, category)
    return SummaryOut(**data)


@router.get("/by-category", response_model=list[CategoryAggItem])
async def by_category(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    rows = await AnalyticsService.by_category(db, start_time, end_time)
    return [CategoryAggItem(**r) for r in rows]
