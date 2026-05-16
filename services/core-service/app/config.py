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

    # Уровень логирования (CORE_LOG_LEVEL): DEBUG/INFO/WARNING/ERROR.
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tbank_loyalt"
    )
    # DSN read-реплики для тяжёлых read-only запросов (история, аналитика).
    # Пусто → весь трафик идёт в primary (безопасный fallback).
    database_replica_url: str | None = None
    db_schema: str = "core"
    db_echo: bool = False

    # Пул соединений SQLAlchemy. Под нагрузкой дефолтный пул (5+10) узок;
    # эти значения — стартовая точка, тюнятся по числу воркеров и max_connections БД.
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # JWT кассира (HS256). Секрет ОБЯЗАН совпадать с PARTNER_JWT_SECRET.
    jwt_secret: str = "dev-tbank-loyalt-cashier-jwt-secret-change-in-prod"

    # Kafka. Если выключена, publisher логирует события, а consumer не стартует.
    # События принимаются вручную через POST /internal/events.
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "core-service"
    kafka_topic_core_events: str = "core.events"
    # core.events — собственные события points.*, проецируемые в read-модель
    # аналитики тем же consumer'ом (дедуп идемпотентен).
    kafka_subscribe_topics: list[str] = Field(
        default_factory=lambda: ["partner.events", "core.events"]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
