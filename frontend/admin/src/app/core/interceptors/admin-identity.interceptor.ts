import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { HEADER_ADMIN_ID } from '@tbank-loyalt/shared';

import { AdminIdentityService } from '../admin-identity.service';

/**
 * Подкладывает X-Admin-Id в каждый исходящий запрос, если администратор
 * выбран. Пустое значение не отправляется — bootstrap-создание первого
 * админа (POST /admins при пустой таблице) не должно видеть заголовок.
 */
export const adminIdentityInterceptor: HttpInterceptorFn = (req, next) => {
  const identity = inject(AdminIdentityService);
  const adminId = identity.adminId();
  if (!adminId) {
    return next(req);
  }
  return next(req.clone({ setHeaders: { [HEADER_ADMIN_ID]: adminId } }));
};
