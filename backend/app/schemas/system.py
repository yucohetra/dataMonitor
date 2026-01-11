from pydantic import BaseModel
from datetime import datetime


class SystemStatusOut(BaseModel):
    generator_running: bool
    ws_clients: int
    buffer_size: int
    batch_interval_sec: int
    last_flush_time: datetime | None
    last_flush_count: int
    last_flush_success: bool
    db_connected: bool


class DbStatusOut(BaseModel):
    db_connected: bool
    db_version: str | None
    server_time: datetime
