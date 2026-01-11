from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # JWT
    JWT_SECRET_KEY: str = "change_this_secret_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Realtime / batching
    ALERT_THRESHOLD: float = 80.0
    BATCH_INTERVAL_SECONDS: int = 5
    GENERATOR_INTERVAL_SECONDS: int = 1
    BUFFER_MAX_SIZE: int = 10000

    # DB
    DB_HOST: str = "db"
    DB_PORT: int = 3306
    DB_NAME: str = "realtime_db"
    DB_USER: str = "realtime_user"
    DB_PASSWORD: str = "realtime_pass"

    @property
    def async_database_url(self) -> str:
        # NOTE:
        # - asyncmy is used to satisfy the requirement of async DB operations with MariaDB.
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def alembic_sync_database_url(self) -> str:
        # NOTE:
        # - Alembic uses a synchronous driver for migrations.
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
