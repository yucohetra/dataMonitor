from datetime import datetime, timezone
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.record import DataRecord
from app.core.config import settings


class RecordService:
    """
    Encapsulates record CRUD, listing, and batch persistence.

    Design considerations:
    - Centralizes query construction to improve readability and testability.
    - Applies anomaly rule consistently across all write paths.
    """

    @staticmethod
    def is_anomaly(value: float) -> bool:
        return value > float(settings.ALERT_THRESHOLD)

    @staticmethod
    async def create(
        session: AsyncSession,
        created_by: int,
        title: str,
        value: float,
        category: str,
        timestamp: datetime | None,
    ) -> DataRecord:
        ts = timestamp or datetime.now(timezone.utc)
        record = DataRecord(
            title=title,
            value=value,
            category=category,
            timestamp=ts,
            is_anomaly=RecordService.is_anomaly(value),
            created_by=created_by,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def get_by_id(session: AsyncSession, record_id: int) -> DataRecord | None:
        row = await session.execute(select(DataRecord).where(DataRecord.id == record_id))
        return row.scalar_one_or_none()

    @staticmethod
    async def update(session: AsyncSession, record: DataRecord, **changes) -> DataRecord:
        for k, v in changes.items():
            if v is None:
                continue
            setattr(record, k, v)

        if "value" in changes and changes["value"] is not None:
            record.is_anomaly = RecordService.is_anomaly(float(changes["value"]))

        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def delete(session: AsyncSession, record: DataRecord) -> None:
        await session.delete(record)
        await session.commit()

    @staticmethod
    async def list_records(
        session: AsyncSession,
        page: int,
        size: int,
        category: str | None,
        is_anomaly: bool | None,
        start_time: datetime | None,
        end_time: datetime | None,
        sort_by: str,
        order: str,
        created_by: int | None = None,
    ) -> tuple[list[DataRecord], int]:
        filters = []
        if category:
            filters.append(DataRecord.category == category)
        if is_anomaly is not None:
            filters.append(DataRecord.is_anomaly == is_anomaly)
        if start_time:
            filters.append(DataRecord.timestamp >= start_time)
        if end_time:
            filters.append(DataRecord.timestamp <= end_time)
        if created_by is not None:
            filters.append(DataRecord.created_by == created_by)

        where_clause = and_(*filters) if filters else None

        sort_map = {
            "timestamp": DataRecord.timestamp,
            "value": DataRecord.value,
            "category": DataRecord.category,
            "id": DataRecord.id,
        }
        sort_col = sort_map.get(sort_by, DataRecord.timestamp)
        sort_expr = desc(sort_col) if order.lower() == "desc" else asc(sort_col)

        count_stmt = select(func.count()).select_from(DataRecord)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total = (await session.execute(count_stmt)).scalar_one()

        stmt = select(DataRecord)
        if where_clause is not None:
            stmt = stmt.where(where_clause)
        stmt = stmt.order_by(sort_expr).offset((page - 1) * size).limit(size)

        items = (await session.execute(stmt)).scalars().all()
        return items, int(total)

    @staticmethod
    async def batch_insert(session: AsyncSession, created_by: int, rows: list[dict]) -> int:
        """
        Persists a batch of records using ORM objects.

        Design considerations:
        - Avoids raw SQL to comply with requirements.
        - Uses a single transaction commit to reduce overhead.
        """
        now = datetime.now(timezone.utc)
        objects = []
        for row in rows:
            ts = row.get("timestamp") or now
            value = float(row["value"])
            objects.append(
                DataRecord(
                    title=str(row["title"]),
                    value=value,
                    category=str(row["category"]),
                    timestamp=ts,
                    is_anomaly=RecordService.is_anomaly(value),
                    created_by=created_by,
                )
            )

        session.add_all(objects)
        await session.commit()
        return len(objects)
