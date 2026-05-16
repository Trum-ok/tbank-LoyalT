import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loyalt_common import RequestIdMiddleware, configure_logging

from app import models  # noqa: F401
from app.config import get_settings
from app.consumer import consumer
from app.domains.devices.router import router as devices_router
from app.domains.inbox.router import router as inbox_router
from app.domains.notifications.router import router as notifications_router

settings = get_settings()
configure_logging(settings.app_name, settings.log_level)

API_DESCRIPTION = """
Сервис уведомлений платформы лояльности **LoyalT**: формирование и доставка
push-уведомлений клиентам Т-Банка.

* **Регистрация устройств** (`/devices`) — приложение Т-Банка по T-ID
  присылает push-токен; повторная регистрация того же токена идемпотентна.
* **Inbox клиента** (`/notifications`) — список уведомлений и отметка
  «прочитано» для экрана уведомлений в приложении.
* **`/internal`** — приём событий (начисление баллов, новые акции,
  сгорание баллов) из Kafka/HTTP; не для внешних клиентов.

По событию сервис создаёт запись уведомления и доставляет её на все
активные устройства клиента. Каждый запрос помечается `X-Request-ID`
(сквозной через HTTP и Kafka), ошибки возвращаются единым телом
`{"detail": "..."}`.
""".strip()

OPENAPI_TAGS = [
    {"name": "devices", "description": "Регистрация push-устройств клиента."},
    {
        "name": "notifications",
        "description": "Inbox клиента: список и отметка о прочтении.",
    },
    {
        "name": "internal",
        "description": "Служебный приём событий, не для внешних клиентов.",
    },
    {"name": "meta", "description": "Здоровье сервиса."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await consumer.start()
    try:
        yield
    finally:
        await consumer.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LoyalT · Notification API",
        summary="Push-уведомления: начисление баллов, акции, сгорание баллов.",
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
        logging.getLogger("notification-service").exception(
            "Unhandled error on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (devices_router, notifications_router, inbox_router):
        app.include_router(router)

    return app


app = create_app()
