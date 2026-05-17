"""Структурное JSON-логирование на stdlib (без сторонних бэкендов).

Один обработчик на root, единый формат для всех сервисов. uvicorn-логгеры
лишаются своих обработчиков и пишутся через тот же форматтер, поэтому
access-логи и логи приложения однородны и агрегируются как есть.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from loyalt_common.context import get_request_id

# Поля LogRecord, которые уже разложены в payload вручную либо неинформативны
# как отдельные ключи — всё прочее из `extra=` попадает в JSON.
_RESERVED = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": self.service,
            "msg": record.getMessage(),
        }
        rid = get_request_id()
        if rid:
            payload["request_id"] = rid
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(service: str, level: str = "INFO") -> None:
    """Перенастраивает root-логгер на единый JSON-вывод в stdout.

    Идемпотентна: повторный вызов заменяет обработчики, не плодит их.
    """
    lvl = level.upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))

    root = logging.getLogger()
    for old in root.handlers[:]:
        root.removeHandler(old)
    root.addHandler(handler)
    root.setLevel(lvl)

    # uvicorn ставит свои обработчики — снимаем, чтобы формат был один.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
