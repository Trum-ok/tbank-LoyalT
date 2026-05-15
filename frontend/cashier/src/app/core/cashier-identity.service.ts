import { Injectable, computed, signal } from '@angular/core';
import { StaffLoginResponse } from '@tbank-loyalt/shared';

const STORAGE_KEY = 'tbank-loyalt-cashier:session';

/**
 * Сессия кассира. До настоящей авторизации (JWT) — это staff_id/partner_id,
 * полученные после входа по коду точки и PIN, сложенные в localStorage.
 * partner_id уходит в core-service как X-Partner-Id, staff_id — как X-Staff-Id.
 */
@Injectable({ providedIn: 'root' })
export class CashierIdentityService {
  private readonly session = signal<StaffLoginResponse | null>(this.restore());

  readonly current = this.session.asReadonly();
  readonly staffId = computed(() => this.session()?.staff_id ?? null);
  readonly partnerId = computed(() => this.session()?.partner_id ?? null);
  readonly partnerName = computed(() => this.session()?.partner_name ?? null);
  readonly staffName = computed(() => this.session()?.staff_name ?? null);
  readonly token = computed(() => this.session()?.access_token ?? null);
  readonly isAuthed = computed(() => this.session() !== null);

  set(session: StaffLoginResponse): void {
    this.session.set(session);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch {
      /* no-op */
    }
  }

  clear(): void {
    this.session.set(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* no-op */
    }
  }

  private restore(): StaffLoginResponse | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw) as StaffLoginResponse;
      }
    } catch {
      /* no-op */
    }
    return null;
  }
}
