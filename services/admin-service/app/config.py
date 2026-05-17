from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ADMIN_",
        extra="ignore",
    )

    app_name: str = "admin-service"
    debug: bool = False

    # Уровень логирования (ADMIN_LOG_LEVEL): DEBUG/INFO/WARNING/ERROR.
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tbank_loyalt"
    )
    db_schema: str = "admin"
    core_schema: str = "core"
    partner_schema: str = "partner"
    db_echo: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # URL соседних сервисов для прокси-вызовов
    partner_service_url: str = "http://localhost:8002"


@lru_cache
def get_settings() -> Settings:
    return Settings()
