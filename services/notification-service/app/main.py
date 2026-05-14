from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (devices_router, notifications_router, inbox_router):
        app.include_router(router)

    return app


app = create_app()
