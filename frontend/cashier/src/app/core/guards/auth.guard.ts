import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { CashierIdentityService } from '../cashier-identity.service';

/** Без активной сессии кассира — на экран входа. */
export const authGuard: CanActivateFn = () => {
  const identity = inject(CashierIdentityService);
  const router = inject(Router);
  return identity.isAuthed() ? true : router.createUrlTree(['/login']);
};

/** Уже вошли — со страницы входа сразу на кассу. */
export const guestGuard: CanActivateFn = () => {
  const identity = inject(CashierIdentityService);
  const router = inject(Router);
  return identity.isAuthed() ? router.createUrlTree(['/pos']) : true;
};
