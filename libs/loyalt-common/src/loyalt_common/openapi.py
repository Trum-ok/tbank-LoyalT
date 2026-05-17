"""Единый контракт ошибок для OpenAPI всех сервисов.

Хендлеры по всей платформе отдают ошибку как `{"detail": "..."}`
(FastAPI HTTPException). Здесь это описано один раз, чтобы Swagger
каждого сервиса показывал реальные коды отказов, а не только 200/422.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Стандартное тело ошибки FastAPI."""

    detail: str = Field(examples=["Понятное сообщение об ошибке"])


_DESCRIPTIONS: dict[int, str] = {
    400: "Некорректный запрос",
    401: "Требуется аутентификация",
    403: "Доступ запрещён",
    404: "Ресурс не найден",
    409: "Конфликт состояния",
    422: "Ошибка валидации входных данных",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, object]]:
    """Готовый блок `responses=` для перечисленных HTTP-кодов.

    Пример: `responses=error_responses(401, 404, 409)` — Swagger покажет
    эти ответы со схемой ErrorResponse и человекочитаемым описанием.
    """
    return {
        code: {
            "model": ErrorResponse,
            "description": _DESCRIPTIONS.get(code, "Ошибка"),
        }
        for code in sorted(set(codes))
    }
