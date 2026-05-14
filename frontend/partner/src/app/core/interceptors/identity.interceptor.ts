import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import {
  HEADER_ACCOUNT_ID,
  HEADER_PARTNER_ID,
} from '@tbank-loyalt/shared';

import { IdentityService } from '../identity.service';

/**
 * Подкладывает X-Account-Id и X-Partner-Id в каждый исходящий HTTP-запрос,
 * исходя из текущей дев-личности. Бэкенд сам валидирует, какой из двух
 * заголовков ему нужен (у разных эндпоинтов разные требования).
 *
 * Пустые значения не отправляются — некоторые публичные эндпоинты (POST
 * /accounts, например) не должны видеть бессмысленные пустые заголовки.
 */
export const identityInterceptor: HttpInterceptorFn = (req, next) => {
  const identity = inject(IdentityService);
  const headers: Record<string, string> = {};

  const accountId = identity.accountId();
  const partnerId = identity.partnerId();
  if (accountId) headers[HEADER_ACCOUNT_ID] = accountId;
  if (partnerId) headers[HEADER_PARTNER_ID] = partnerId;

  if (Object.keys(headers).length === 0) {
    return next(req);
  }
  return next(req.clone({ setHeaders: headers }));
};
