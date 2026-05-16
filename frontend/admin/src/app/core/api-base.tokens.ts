import { InjectionToken } from '@angular/core';
import { DEFAULT_ADMIN_BASE_URL } from '@tbank-loyalt/shared';

export const ADMIN_API_BASE = new InjectionToken<string>('ADMIN_API_BASE', {
  factory: () => DEFAULT_ADMIN_BASE_URL,
});
