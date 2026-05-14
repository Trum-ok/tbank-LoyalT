from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# noqa: F401 — импорт всех моделей для регистрации в Base.metadata
from app import models  # noqa: F401
from app.config import get_settings
from app.domains.catalog.router import router as catalog_router
from app.domains.enrollments.router import router as enrollments_router
from app.domains.partners.router import router as partners_router
from app.domains.points.router import customer_router as balance_router
from app.domains.points.router import partner_router as points_router
from app.domains.programs.router import router as programs_router
from app.domains.rewards.router import router as rewards_router
from app.domains.transactions.router import (
    customer_router as tx_customer_router,
)
from app.domains.transactions.router import (
    partner_router as tx_partner_router,
)

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
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
        partners_router,
        programs_router,
        rewards_router,
        catalog_router,
        enrollments_router,
        points_router,
        balance_router,
        tx_customer_router,
        tx_partner_router,
    ):
        app.include_router(router)

    return app


app = create_app()
