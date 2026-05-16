import { Injectable, computed, signal } from '@angular/core';

export interface AdminIdentity {
  admin_id: string | null;
  email: string | null;
  label: string;
}

const STORAGE_KEY = 'tbank-loyalt-admin:identity';

const GUEST: AdminIdentity = {
  admin_id: null,
  email: null,
  label: 'Не авторизован',
};

/**
 * Текущая "личность" сотрудника Т-Банка в админ-панели.
 *
 * До настоящей авторизации (JWT помечен TODO в admin-service) — это просто
 * X-Admin-Id, который выбирается на экране входа: либо bootstrap первого
 * администратора (когда таблица пуста), либо выбор из существующих.
 * Значение хранится в localStorage и подкладывается интерцептором.
 */
@Injectable({ providedIn: 'root' })
export class AdminIdentityService {
  private readonly state = signal<AdminIdentity>(this.restore());

  readonly current = this.state.asReadonly();
  readonly adminId = computed(() => this.state().admin_id);
  readonly isAuthenticated = computed(() => this.state().admin_id !== null);

  set(identity: AdminIdentity): void {
    this.state.set(identity);
    this.persist();
  }

  clear(): void {
    this.state.set(GUEST);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* no-op */
    }
  }

  private persist(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state()));
    } catch {
      /* no-op */
    }
  }

  private restore(): AdminIdentity {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw) as AdminIdentity;
      }
    } catch {
      /* no-op */
    }
    return GUEST;
  }
}
