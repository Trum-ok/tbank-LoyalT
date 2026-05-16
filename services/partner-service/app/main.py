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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await publisher.start()
    try:
        yield
    finally:
        await publisher.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
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
