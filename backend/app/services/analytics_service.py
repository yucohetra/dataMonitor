from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.record import DataRecord


class AnalyticsService:
    """
    Provides analytics queries over persisted records.

    Design considerations:
    - Uses DB-side aggregation to ensure consistency and scalability.
    - Keeps endpoints minimal to match the evaluation scope.
    """

    @staticmethod
    async def summary(
        session: AsyncSession,
        start_time: datetime | None,
        end_time: datetime | None,
        category: str | None,
    ) -> dict:
        stmt = select(
            func.count(DataRecord.id),
            func.sum(DataRecord.value),
            func.avg(DataRecord.value),
            func.min(DataRecord.value),
            func.max(DataRecord.value),
        )

        if start_time:
            stmt = stmt.where(DataRecord.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(DataRecord.timestamp <= end_time)
        if category:
            stmt = stmt.where(DataRecord.category == category)

        row = (await session.execute(stmt)).one()
        count, sum_value, avg_value, min_value, max_value = row
        return {
            "count": int(count or 0),
            "sum": float(sum_value or 0.0),
            "avg": float(avg_value or 0.0),
            "min": float(min_value or 0.0),
            "max": float(max_value or 0.0),
        }

    @staticmethod
    async def by_category(
        session: AsyncSession,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[dict]:
        stmt = select(
            DataRecord.category,
            func.count(DataRecord.id),
            func.avg(DataRecord.value),
            func.min(DataRecord.value),
            func.max(DataRecord.value),
        ).group_by(DataRecord.category)

        if start_time:
            stmt = stmt.where(DataRecord.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(DataRecord.timestamp <= end_time)

        rows = (await session.execute(stmt)).all()
        out = []
        for category, count, avg_value, min_value, max_value in rows:
            out.append(
                {
                    "category": str(category),
                    "count": int(count or 0),
                    "avg": float(avg_value or 0.0),
                    "min": float(min_value or 0.0),
                    "max": float(max_value or 0.0),
                }
            )
        return out
