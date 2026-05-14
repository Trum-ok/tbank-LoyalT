from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CORE_",
        extra="ignore",
    )

    app_name: str = "core-service"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tbank_loyalt"
    )
    db_schema: str = "core"
    db_echo: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Kafka. Если выключена, publisher логирует события, а consumer не стартует.
    # События принимаются вручную через POST /internal/events.
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "core-service"
    kafka_topic_core_events: str = "core.events"
    kafka_subscribe_topics: list[str] = Field(default_factory=lambda: ["partner.events"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
