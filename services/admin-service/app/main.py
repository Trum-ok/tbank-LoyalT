import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loyalt_common import RequestIdMiddleware, configure_logging

from app import models  # noqa: F401
from app.clients.partner import partner_client
from app.config import get_settings
from app.domains.admins.router import router as admins_router
from app.domains.catalog.router import router as catalog_router
from app.domains.metrics.router import router as metrics_router
from app.domains.moderation.router import (
    applications_router as moderation_applications_router,
)
from app.domains.moderation.router import partners_router as moderation_partners_router

settings = get_settings()
configure_logging(settings.app_name, settings.log_level)

API_DESCRIPTION = """
Панель Т-Банка для платформы лояльности **LoyalT**: модерация заявок
партнёров, управление витриной каталога, блокировка партнёров, сводные
метрики платформы и собственная авторизация администратора.

* **`/admins`** — учётные записи администраторов (bootstrap первого
  админа, список, профиль, активация/деактивация).
* **`/moderation`** — прокси поверх partner-service: рассмотрение заявок
  (одобрение/отклонение) и управление статусом партнёров (блокировка,
  приостановка, разблокировка).
* **`/catalog`** — витрина для приложения Т-Банка: категории,
  избранные партнёры, рекламные баннеры.
* **`/metrics`** — агрегаты для дашборда Т-Банка по платформе в целом.

Авторизация — по заголовку `X-Admin-Id` (временно, до подключения JWT).
Каждый запрос помечается `X-Request-ID` (сквозной через HTTP и Kafka),
ошибки возвращаются единым телом `{"detail": "..."}`.
""".strip()

OPENAPI_TAGS = [
    {"name": "admins", "description": "Учётные записи администраторов Т-Банка."},
    {
        "name": "moderation",
        "description": "Модерация заявок и управление статусом партнёров.",
    },
    {
        "name": "catalog",
        "description": "Витрина каталога: категории, избранное, баннеры.",
    },
    {"name": "metrics", "description": "Сводные метрики платформы для дашборда."},
    {"name": "meta", "description": "Здоровье сервиса."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await partner_client.start()
    try:
        yield
    finally:
        await partner_client.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LoyalT · Admin API",
        summary="Модерация партнёров, каталог, метрики и админы платформы.",
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
        logging.getLogger("admin-service").exception(
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
        admins_router,
        moderation_applications_router,
        moderation_partners_router,
        catalog_router,
        metrics_router,
    ):
        app.include_router(router)

    return app


app = create_app()
