# loyalt-common

Общий код платформы LoyalT, разделяемый всеми сервисами через uv-workspace.

- `logging` — структурное JSON-логирование (stdlib, без сторонних бэкендов).
- `context` — `request_id` в `contextvars`, сквозной через HTTP и Kafka.
- `middleware` — ASGI-middleware, проставляющий `X-Request-ID`.
- `kafka` — проброс `request_id` в конверте событий и обратно.
