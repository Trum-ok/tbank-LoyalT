"""Хранилище логотипов партнёров в MinIO (S3-совместимое API).

Bucket делается публичным на чтение (anonymous `s3:GetObject`), поэтому
`logo_url` — стабильная прямая ссылка, которую браузер клиента отдаёт в
`<img>` без подписи и без проксирования через сервис.

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
EXT_BY_CONTENT_TYPE: dict[str, str] = {
    "image/png": "png",
    "image/svg+xml": "svg",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}

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
        ContentType=content_type,
        CacheControl="public, max-age=300",
    )


async def upload_logo(partner_id: UUID, data: bytes, content_type: str) -> str:
    """Загрузить логотип и вернуть публичный URL для сохранения в `logo_url`.

    Ключ объекта детерминированный (`<partner_id>.<ext>`) — повторная
    загрузка перезаписывает старый файл. `?v=<ts>` сбрасывает кэш браузера.
    """
    ext = EXT_BY_CONTENT_TYPE[content_type]
    key = f"{partner_id}.{ext}"
    await run_in_threadpool(_put, key, data, content_type)
    s = get_settings()
    return f"{s.s3_public_url.rstrip('/')}/{s.s3_bucket}/{key}?v={int(time.time())}"
