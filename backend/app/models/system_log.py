from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False)  # INFO/WARN/ERROR
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # AUTH/DATA_IMPORT/WS/DB/SYSTEM
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str] = mapped_column(String(2048), nullable=True)

    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
