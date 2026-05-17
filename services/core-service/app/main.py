import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loyalt_common import RequestIdMiddleware, configure_logging

from app import models  # noqa: F401 — регистрация моделей для Alembic
from app.config import get_settings
from app.consumer import consumer
from app.database import SessionLocal
from app.domains.analytics.router import partner_router as analytics_router
from app.domains.catalog.router import router as catalog_router
from app.domains.enrollments.router import router as enrollments_router
from app.domains.partners.router import router as partners_router
from app.domains.points.expiration import run_expiration
from app.domains.points.router import customer_router as balance_router
from app.domains.points.router import partner_router as points_router
from app.domains.programs.router import router as programs_router
from app.domains.rewards.router import router as rewards_router
from app.domains.transactions.router import customer_router as tx_customer_router
from app.domains.transactions.router import partner_router as tx_partner_router
from app.events import publisher
from app.internal_router import router as internal_router

settings = get_settings()
configure_logging(settings.app_name, settings.log_level)

API_DESCRIPTION = """
Ядро платформы лояльности **LoyalT**: программы и правила начисления, каталог
наград, начисление/списание баллов, история и отмена транзакций, баланс и
подключённые программы клиента.

* **Партнёрские** ручки (`/points`, `/programs`, …) вызывает касса/ЛК партнёра.
* **Клиентские** ручки (`/balance`, `/catalog`) — приложение Т-Банка по T-ID.
* **`/internal`** — служебный приём событий, не для внешних клиентов.

Каждый запрос помечается `X-Request-ID` (сквозной через HTTP и Kafka),
ошибки возвращаются единым телом `{"detail": "..."}`.
""".strip()

OPENAPI_TAGS = [
    {"name": "partners", "description": "Карточки партнёров и их публичные данные."},
    {"name": "programs", "description": "Программы лояльности и правила начисления."},
    {"name": "rewards", "description": "Каталог наград программы."},
    {"name": "catalog", "description": "Витрина программ для клиента."},
    {"name": "enrollments", "description": "Подключение клиента к программе."},
    {"name": "points", "description": "Начисление, списание и отмена баллов (касса)."},
    {"name": "balance", "description": "Баланс и подключённые программы клиента."},
    {"name": "transactions", "description": "История операций по баллам."},
    {"name": "analytics", "description": "Агрегаты для дашборда партнёра."},
    {"name": "internal", "description": "Служебные ручки, не для внешних клиентов."},
    {"name": "meta", "description": "Здоровье сервиса."},
]


async def _expiration_loop() -> None:
    """Периодический прогон сгорания баллов (если джоб включён)."""
    interval = max(60, settings.expire_job_interval_seconds)
    log = logging.getLogger("core-service")
    while True:
        try:
            async with SessionLocal() as session:
                await run_expiration(session)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Scheduled points expiration run failed")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await publisher.start()
    await consumer.start()
    expire_task: asyncio.Task[None] | None = None
    if settings.expire_job_enabled:
        expire_task = asyncio.create_task(
            _expiration_loop(), name="points-expiration"
        )
    try:
        yield
    finally:
        if expire_task is not None:
            expire_task.cancel()
            try:
                await expire_task
            except asyncio.CancelledError:
                pass
        await consumer.stop()
        await publisher.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LoyalT · Core API",
        summary="Программы лояльности, баллы, транзакции и баланс клиента.",
        description=API_DESCRIPTION,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
        contact={
            "name": "Команда LLM Chads",
            "url": "https://github.com/Trum-ok/tbank-loyalt",
        },
        license_info={
            "name": "MIT",
            "url": "https://github.com/Trum-ok/tbank-loyalt/blob/master/LICENSE",
        },
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Добавлен последним → внешний слой: request_id проставляется до CORS,
    # роутинга и обработчика 500, поэтому есть во всех логах запроса.
    app.add_middleware(RequestIdMiddleware)

    # Starlette по умолчанию формирует 500 минуя CORSMiddleware, из-за чего
    # браузер блокирует ответ как нарушающий CORS. Перехватываем все
    # необработанные исключения сами — тогда middleware успевает наложить
    # Access-Control-Allow-Origin.
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("core-service").exception(
            "Unhandled error on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (
        partners_router,
        programs_router,
        rewards_router,
        catalog_router,
        enrollments_router,
        points_router,
        balance_router,
        tx_customer_router,
        tx_partner_router,
        analytics_router,
        internal_router,
    ):
        app.include_router(router)

    return app


app = create_app()
