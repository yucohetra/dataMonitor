from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_log import SystemLog


class LogService:
    """
    Persists important system events into the database.

    Design considerations:
    - Stores only high-signal events to avoid excessive write volume.
    - Keeps log schema simple to support basic filtering and auditing.
    """

    @staticmethod
    async def write(
        session: AsyncSession,
        level: str,
        event_type: str,
        message: str,
        detail: str | None = None,
        actor_user_id: int | None = None,
    ) -> None:
        session.add(
            SystemLog(
                level=level,
                event_type=event_type,
                message=message,
                detail=detail,
                actor_user_id=actor_user_id,
            )
        )
        await session.commit()
