"""HTTP-клиент к partner-service для админских операций.

partner-service уже умеет модерацию под `X-Admin-Id` — admin-service
просто перенаправляет туда вызовы, добавляя заголовок из своего auth.
Реализован через один разделяемый AsyncClient (запускается в lifespan).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.config import get_settings
from app.errors import UpstreamError


class PartnerServiceClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._settings.partner_service_url,
            timeout=httpx.Timeout(10.0),
        )

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("PartnerServiceClient is not started")
        return self._client

    @staticmethod
    def _headers(admin_id: UUID) -> dict[str, str]:
        return {"X-Admin-Id": str(admin_id)}

    async def _request(
        self,
        method: str,
        path: str,
        admin_id: UUID,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        client = self._ensure()
        response = await client.request(
            method, path, params=params, json=json, headers=self._headers(admin_id)
        )
        if response.is_success:
            if response.status_code == httpx.codes.NO_CONTENT:
                return None
            return response.json()
        raise UpstreamError("partner-service", response.status_code, response.text)

    # --- applications ---

    async def list_applications(
        self,
        admin_id: UUID,
        *,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status_filter:
            params["status"] = status_filter
        return await self._request(
            "GET", "/admin/applications", admin_id, params=params
        )

    async def get_application(
        self, admin_id: UUID, application_id: UUID
    ) -> dict[str, Any]:
        return await self._request(
            "GET", f"/admin/applications/{application_id}", admin_id
        )

    async def approve_application(
        self, admin_id: UUID, application_id: UUID, comment: str | None
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/admin/applications/{application_id}/approve",
            admin_id,
            json={"comment": comment},
        )

    async def reject_application(
        self, admin_id: UUID, application_id: UUID, comment: str | None
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/admin/applications/{application_id}/reject",
            admin_id,
            json={"comment": comment},
        )

    # --- partners ---

    async def list_partners(
        self,
        admin_id: UUID,
        *,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status_filter:
            params["status"] = status_filter
        return await self._request("GET", "/admin/partners", admin_id, params=params)

    async def get_partner(self, admin_id: UUID, partner_id: UUID) -> dict[str, Any]:
        return await self._request("GET", f"/admin/partners/{partner_id}", admin_id)

    async def suspend_partner(self, admin_id: UUID, partner_id: UUID) -> dict[str, Any]:
        return await self._request(
            "POST", f"/admin/partners/{partner_id}/suspend", admin_id
        )

    async def block_partner(self, admin_id: UUID, partner_id: UUID) -> dict[str, Any]:
        return await self._request(
            "POST", f"/admin/partners/{partner_id}/block", admin_id
        )

    async def unblock_partner(self, admin_id: UUID, partner_id: UUID) -> dict[str, Any]:
        return await self._request(
            "POST", f"/admin/partners/{partner_id}/unblock", admin_id
        )


partner_client = PartnerServiceClient()
