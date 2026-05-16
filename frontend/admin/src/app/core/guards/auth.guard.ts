import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AdminIdentityService } from '../admin-identity.service';

/** Пускает в админ-панель только после выбора администратора. */
export const authGuard: CanActivateFn = () => {
  const identity = inject(AdminIdentityService);
  const router = inject(Router);
  if (identity.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/login']);
};
