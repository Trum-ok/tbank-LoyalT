import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401
from app.config import get_settings
from app.consumer import consumer
from app.domains.devices.router import router as devices_router
from app.domains.inbox.router import router as inbox_router
from app.domains.notifications.router import router as notifications_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await consumer.start()
    try:
        yield
    finally:
        await consumer.stop()


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
