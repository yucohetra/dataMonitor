from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings

# NOTE:
# - pool_pre_ping reduces failures caused by stale connections in containerized environments.
# - pool_size is intentionally conservative for a small evaluation workload.
engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def db_ping() -> bool:
    """
    Checks database connectivity using a lightweight query.

    Design considerations:
    - Avoids heavy introspection to keep the endpoint fast and reliable.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
