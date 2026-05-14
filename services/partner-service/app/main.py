from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 — регистрация моделей для Alembic
from app.config import get_settings
from app.domains.accounts.router import router as accounts_router
from app.domains.applications.router import admin_router as applications_admin_router
from app.domains.applications.router import partner_router as applications_partner_router
from app.domains.partners.router import admin_router as partners_admin_router
from app.domains.partners.router import partner_router as partners_partner_router
from app.events import publisher

settings = get_settings()


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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    ):
        app.include_router(router)

    return app


app = create_app()
