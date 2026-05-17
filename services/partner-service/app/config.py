from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Публично известный sentinel из репозитория. Используется ТОЛЬКО как
# маркер «секрет не переопределён». Любое другое значение проходит.
_DEV_JWT_SECRET = "dev-tbank-loyalt-cashier-jwt-secret-change-in-prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PARTNER_",
        extra="ignore",
    )

    app_name: str = "partner-service"
    debug: bool = False

    # Уровень логирования (PARTNER_LOG_LEVEL): DEBUG/INFO/WARNING/ERROR.
    log_level: str = "INFO"

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
    # При debug=False дефолтный sentinel приводит к фейл-фасту (см. ниже).
    jwt_secret: str = _DEV_JWT_SECRET
    jwt_ttl_hours: int = 12

    # Kafka. Если bootstrap не задан или kafka_enabled=False, producer работает в
    # stub-режиме и просто логирует события.
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_partner_events: str = "partner.events"

    # MinIO / S3-совместимое хранилище логотипов партнёров.
    # s3_endpoint_url — адрес для SDK (внутри docker-сети это http://minio:9000).
    # s3_public_url — базовый URL, который видит браузер клиента и который
    # сохраняется в logo_url (на хосте это http://localhost:9000).
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    s3_bucket: str = "partner-logos"
    # Лимит размера загружаемого логотипа, байт (по умолчанию 2 МБ).
    logo_max_bytes: int = 2 * 1024 * 1024

    @model_validator(mode="after")
    def _forbid_default_jwt_secret_in_prod(self) -> "Settings":
        # Фейл-фаст: вне dev (debug=False) запрещаем работать на публично
        # известном секрете — иначе кто угодно подделает токен кассы.
        if not self.debug and self.jwt_secret == _DEV_JWT_SECRET:
            raise ValueError(
                "PARTNER_JWT_SECRET не переопределён (используется публичный "
                "dev-секрет из репозитория). Задайте PARTNER_JWT_SECRET "
                "(совпадающий с CORE_JWT_SECRET) или включите PARTNER_DEBUG=true "
                "для локальной разработки."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
