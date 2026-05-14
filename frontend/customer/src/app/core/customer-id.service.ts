import { Injectable, computed, signal } from '@angular/core';

export interface CustomerProfile {
  id: string;
  label: string;
}

const STORAGE_KEY = 'tbank-loyalt:customer-id';

const DEFAULT_PROFILES: CustomerProfile[] = [
  { id: '11111111-1111-1111-1111-111111111111', label: 'Анна (демо)' },
  { id: '22222222-2222-2222-2222-222222222222', label: 'Борис (демо)' },
  { id: '33333333-3333-3333-3333-333333333333', label: 'Виктория (демо)' },
];

@Injectable({ providedIn: 'root' })
export class CustomerIdService {
  private readonly _currentId = signal<string>(this.restoreId());
  readonly profiles = signal<CustomerProfile[]>(DEFAULT_PROFILES);
  readonly currentId = this._currentId.asReadonly();
  readonly currentProfile = computed<CustomerProfile>(() => {
    const id = this._currentId();
    return (
      this.profiles().find(p => p.id === id) ?? {
        id,
        label: `custom · ${id.slice(0, 8)}`,
      }
    );
  });

  setId(id: string): void {
    this._currentId.set(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* no-op */
    }
  }

  private restoreId(): string {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return stored;
      }
    } catch {
      /* no-op */
    }
    return DEFAULT_PROFILES[0].id;
  }
}
