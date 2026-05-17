import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loyalt_common import RequestIdMiddleware, configure_logging

from app import models  # noqa: F401 — регистрация моделей для Alembic
from app.config import get_settings
from app.domains.accounts.router import router as accounts_router
from app.domains.applications.router import admin_router as applications_admin_router
from app.domains.applications.router import (
    partner_router as applications_partner_router,
)
from app.domains.broadcasts.router import router as broadcasts_router
from app.domains.partners.router import admin_router as partners_admin_router
from app.domains.partners.router import partner_router as partners_partner_router
from app.domains.staff.router import auth_router as staff_auth_router
from app.domains.staff.router import router as staff_router
from app.events import publisher

settings = get_settings()
configure_logging(settings.app_name, settings.log_level)

API_DESCRIPTION = """
Личный кабинет партнёра платформы лояльности **LoyalT**: регистрация бизнеса,
заявки на модерацию, профиль партнёра, сотрудники кассы и рассылки клиентам.

* **Аккаунт и заявка** (`/accounts`, `/applications`) — предприниматель
  регистрируется и подаёт заявку, админ Т-Банка одобряет/отклоняет её.
* **Профиль партнёра** (`/partners`) — карточка одобренного бизнеса, логотип
  и брендирование (видны в каталоге клиента).
* **Сотрудники** (`/staff`) — кассиры партнёра; вход кассы по коду и PIN
  выдаёт JWT для вызова ручек начисления баллов в core-service.
* **Рассылки** (`/broadcasts`) — сегментированные сообщения клиентам через
  notification-service.
* **`/admin/...`** — служебные ручки модерации для панели Т-Банка.

Каждый запрос помечается `X-Request-ID` (сквозной через HTTP и Kafka),
ошибки возвращаются единым телом `{"detail": "..."}`.
""".strip()

OPENAPI_TAGS = [
    {
        "name": "accounts",
        "description": "Регистрация и профиль аккаунта предпринимателя.",
    },
    {
        "name": "applications",
        "description": "Заявка партнёра на подключение к платформе.",
    },
    {
        "name": "applications-admin",
        "description": "Модерация заявок панелью Т-Банка.",
    },
    {
        "name": "partners",
        "description": "Профиль одобренного партнёра и брендирование.",
    },
    {
        "name": "partners-admin",
        "description": "Управление статусом партнёров панелью Т-Банка.",
    },
    {"name": "broadcasts", "description": "Рассылки клиентам по сегментам."},
    {"name": "staff-auth", "description": "Вход кассы по коду и PIN, выдача JWT."},
    {"name": "staff", "description": "Управление кассирами из ЛК партнёра."},
    {"name": "meta", "description": "Здоровье сервиса."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await publisher.start()
    try:
        yield
    finally:
        await publisher.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LoyalT · Partner API",
        summary="ЛК партнёра: регистрация бизнеса, заявки, профиль, кассиры, рассылки.",
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
        logging.getLogger("partner-service").exception(
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
        accounts_router,
        applications_partner_router,
        applications_admin_router,
        partners_partner_router,
        partners_admin_router,
        broadcasts_router,
        staff_auth_router,
        staff_router,
    ):
        app.include_router(router)

    return app


app = create_app()
