import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { CashierIdentityService } from '../cashier-identity.service';

/**
 * Подкладывает Authorization: Bearer <jwt> в исходящие запросы. Токен
 * выдаётся partner-service на /staff/login; core-service достаёт из него
 * partner_id. Публичный /staff/login токена ещё не имеет — уходит без него.
 *
 * На 401 (протух/невалиден токен) — сбрасываем сессию и на экран входа.
 */
export const staffInterceptor: HttpInterceptorFn = (req, next) => {
  const identity = inject(CashierIdentityService);
  const router = inject(Router);

  const token = identity.token();
  const authed = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authed).pipe(
    catchError((err: unknown) => {
      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        identity.isAuthed()
      ) {
        identity.clear();
        void router.navigate(['/login']);
      }
      return throwError(() => err);
    }),
  );
};
