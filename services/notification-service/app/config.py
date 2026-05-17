from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOTIFICATION_",
        extra="ignore",
    )

    app_name: str = "notification-service"
    debug: bool = False

    # Уровень логирования (NOTIFICATION_LOG_LEVEL): DEBUG/INFO/WARNING/ERROR.
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tbank_loyalt"
    )
    db_schema: str = "notification"
    db_echo: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Kafka. Когда выключен, consumer не стартует и события можно
    # принимать через POST /internal/events (для локального теста).
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "notification-service"
    kafka_topics: list[str] = Field(
        default_factory=lambda: ["core.events", "partner.events"]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
