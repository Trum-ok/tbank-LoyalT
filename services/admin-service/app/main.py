from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.clients.partner import partner_client
from app.config import get_settings
from app.domains.admins.router import router as admins_router
from app.domains.catalog.router import router as catalog_router
from app.domains.metrics.router import router as metrics_router
from app.domains.moderation.router import (
    applications_router as moderation_applications_router,
)
from app.domains.moderation.router import (
    partners_router as moderation_partners_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await partner_client.start()
    try:
        yield
    finally:
        await partner_client.stop()


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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
