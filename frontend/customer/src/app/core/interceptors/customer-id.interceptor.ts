import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { HEADER_CUSTOMER_ID } from '@tbank-loyalt/shared';

import { CustomerIdService } from '../customer-id.service';

export const customerIdInterceptor: HttpInterceptorFn = (req, next) => {
  const customerId = inject(CustomerIdService).currentId();
  return next(req.clone({ setHeaders: { [HEADER_CUSTOMER_ID]: customerId } }));
};
