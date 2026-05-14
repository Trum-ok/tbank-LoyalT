import { InjectionToken } from '@angular/core';
import {
  DEFAULT_CORE_BASE_URL,
  DEFAULT_PARTNER_BASE_URL,
} from '@tbank-loyalt/shared';

export const CORE_API_BASE = new InjectionToken<string>('CORE_API_BASE', {
  factory: () => DEFAULT_CORE_BASE_URL,
});

export const PARTNER_API_BASE = new InjectionToken<string>('PARTNER_API_BASE', {
  factory: () => DEFAULT_PARTNER_BASE_URL,
});
