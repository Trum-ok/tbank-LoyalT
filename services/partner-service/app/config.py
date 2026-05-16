from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PARTNER_",
        extra="ignore",
    )

    app_name: str = "partner-service"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tbank_loyalt"
    )
    db_schema: str = "partner"
    db_echo: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Внутренний REST-вызов в core-service (резолв аудитории рассылок).
    core_base_url: str = "http://localhost:8001"

    # JWT кассира (HS256). Секрет ОБЯЗАН совпадать с CORE_JWT_SECRET,
    # иначе core-service не примет токен кассы.
    jwt_secret: str = "dev-tbank-loyalt-cashier-jwt-secret-change-in-prod"
    jwt_ttl_hours: int = 12

    # Kafka. Если bootstrap не задан или kafka_enabled=False, producer работает в
    # stub-режиме и просто логирует события.
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_partner_events: str = "partner.events"


@lru_cache
def get_settings() -> Settings:
    return Settings()
