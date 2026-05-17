# loyalt-common

Общий код платформы LoyalT, разделяемый всеми сервисами через uv-workspace.

- `logging` — структурное JSON-логирование (stdlib, без сторонних бэкендов):
  `configure_logging`.
- `context` — `request_id` в `contextvars`, сквозной через HTTP и Kafka:
  `get_request_id`, `set_request_id`, `request_id_ctx`.
- `middleware` — ASGI-middleware, проставляющий `X-Request-ID`:
  `RequestIdMiddleware`.
- `kafka` — проброс `request_id` в конверте событий и обратно:
  `with_request_id`, `bind_request_id`.
- `openapi` — единый контракт ошибок для Swagger: модель `ErrorResponse`
  (`{"detail": "..."}`) и хелпер `error_responses(401, 404, …)` для
  `responses=` в роутерах.
