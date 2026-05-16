import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401 — регистрация моделей для Alembic
from app.config import get_settings
from app.consumer import consumer
from app.domains.analytics.router import partner_router as analytics_router
from app.domains.catalog.router import router as catalog_router
from app.domains.enrollments.router import router as enrollments_router
from app.domains.partners.router import router as partners_router
from app.domains.points.router import customer_router as balance_router
from app.domains.points.router import partner_router as points_router
from app.domains.programs.router import router as programs_router
from app.domains.rewards.router import router as rewards_router
from app.domains.transactions.router import customer_router as tx_customer_router
from app.domains.transactions.router import partner_router as tx_partner_router
from app.events import publisher
from app.internal_router import router as internal_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await publisher.start()
    await consumer.start()
    try:
        yield
    finally:
        await consumer.stop()
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
