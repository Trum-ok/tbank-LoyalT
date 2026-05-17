"""Хранилище логотипов партнёров в MinIO (S3-совместимое API).

Bucket делается публичным на чтение (anonymous `s3:GetObject`), поэтому
`logo_url` — стабильная прямая ссылка, которую браузер клиента отдаёт в
`<img>` без подписи и без проксирования через сервис.

Так как объект отдаётся напрямую браузеру, тип файла определяется по
сигнатуре содержимого (magic bytes), а НЕ по клиентскому `Content-Type`
— иначе можно залить SVG/HTML со `<script>` и получить stored XSS на
домене хранилища. Принимаются только растровые форматы (SVG не
поддерживается принципиально: он исполняемый и санитайзера в
зависимостях нет). Объект сохраняется с проверенным `Content-Type` и
`Content-Disposition: inline`, чтобы браузер не пытался переинтерпретировать
содержимое.

boto3 синхронный, поэтому блокирующие вызовы уводим в threadpool —
хендлеры остаются `async` (требование CLAUDE.md).
"""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from typing import Any
from uuid import UUID

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings

logger = logging.getLogger("partner.storage")

# Допустимые типы логотипа и соответствующее расширение объекта.
# SVG исключён намеренно: он может содержать исполняемый <script>, а
# санитайзера в зависимостях нет — при прямой отдаче из публичного
# бакета это stored XSS.
EXT_BY_CONTENT_TYPE: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


class UnsupportedImageError(ValueError):
    """Содержимое файла не является поддерживаемым растровым изображением."""


def detect_content_type(data: bytes) -> str:
    """Определяет тип изображения по сигнатуре байтов (magic bytes).

    Возвращает канонический `Content-Type`. Бросает `UnsupportedImageError`,
    если содержимое не PNG/JPEG/WebP. Клиентский заголовок `Content-Type`
    здесь сознательно игнорируется — ему доверять нельзя.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise UnsupportedImageError(
        "Файл не является корректным PNG, JPEG или WebP изображением"
    )


# Bucket-политику достаточно проставить один раз на процесс.
_bucket_ready = False


@lru_cache
def _client() -> Any:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _ensure_bucket() -> None:
    global _bucket_ready
    if _bucket_ready:
        return
    s = get_settings()
    client = _client()
    try:
        client.head_bucket(Bucket=s.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=s.s3_bucket)
    # Anonymous read-only — иначе браузер клиента не сможет открыть картинку.
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{s.s3_bucket}/*"],
            }
        ],
    }
    client.put_bucket_policy(Bucket=s.s3_bucket, Policy=json.dumps(policy))
    _bucket_ready = True


def _put(key: str, data: bytes, content_type: str) -> None:
    s = get_settings()
    _ensure_bucket()
    _client().put_object(
        Bucket=s.s3_bucket,
        Key=key,
        Body=data,
        # content_type — результат detect_content_type (проверен по байтам).
        ContentType=content_type,
        # Браузер не должен пытаться «угадать» тип и рендерить содержимое
        # как документ — отдаём как вложенное изображение явно.
        ContentDisposition="inline",
        CacheControl="public, max-age=300",
        Metadata={"x-content-type-options": "nosniff"},
    )


async def upload_logo(partner_id: UUID, data: bytes) -> str:
    """Загрузить логотип и вернуть публичный URL для сохранения в `logo_url`.

    Тип файла определяется по содержимому (`detect_content_type`), не по
    клиентскому заголовку. Бросает `UnsupportedImageError`, если это не
    PNG/JPEG/WebP. Ключ объекта детерминированный (`<partner_id>.<ext>`)
    — повторная загрузка перезаписывает старый файл; `?v=<ts>` сбрасывает
    кэш браузера.
    """
    content_type = detect_content_type(data)
    ext = EXT_BY_CONTENT_TYPE[content_type]
    key = f"{partner_id}.{ext}"
    await run_in_threadpool(_put, key, data, content_type)
    s = get_settings()
    return f"{s.s3_public_url.rstrip('/')}/{s.s3_bucket}/{key}?v={int(time.time())}"
