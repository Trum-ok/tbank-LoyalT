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
    # При debug=False дефолтный sentinel приводит к фейл-фасту (см. ниже).
    jwt_secret: str = _DEV_JWT_SECRET

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

    # Фоновый джоб сгорания баллов. Когда выключен — сгорание запускается
    # только вручную через POST /internal/jobs/expire-points (cron/демо).
    expire_job_enabled: bool = False
    expire_job_interval_seconds: int = 3600

    # Фоновый джоб бонусных кампаний. Запускается раз в сутки.
    bonus_campaigns_job_enabled: bool = False
    bonus_campaigns_job_interval_seconds: int = 86400

    @model_validator(mode="after")
    def _forbid_default_jwt_secret_in_prod(self) -> "Settings":
        # Фейл-фаст: вне dev (debug=False) запрещаем работать на публично
        # известном секрете — иначе кто угодно подделает токен кассы.
        if not self.debug and self.jwt_secret == _DEV_JWT_SECRET:
            raise ValueError(
                "CORE_JWT_SECRET не переопределён (используется публичный "
                "dev-секрет из репозитория). Задайте CORE_JWT_SECRET "
                "(совпадающий с PARTNER_JWT_SECRET) или включите CORE_DEBUG=true "
                "для локальной разработки."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
