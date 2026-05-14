import { Injectable, computed, signal } from '@angular/core';

export interface PartnerIdentity {
  account_id: string | null;
  partner_id: string | null;
  label: string;
}

const STORAGE_KEY = 'tbank-loyalt-partner:identity';

// Реальные UUID берутся из тестовых данных core-service / partner-service.
// Чтобы поменять — посмотрите `curl http://localhost:8001/partners` и
// подложите id существующего партнёра, иначе FK-ограничения дадут 500/409.
const DEMO_IDENTITIES: PartnerIdentity[] = [
  {
    account_id: '11111111-1111-1111-1111-111111111111',
    partner_id: '1f6ea13f-7ddb-4a0a-82e9-6308a2616267',
    label: 'Кофе Хауз (демо)',
  },
  {
    account_id: null,
    partner_id: null,
    label: 'Свежий партнёр (онбординг)',
  },
];

/**
 * Управляет текущей "личностью" пользователя кабинета партнёра.
 *
 * До настоящей авторизации (JWT) — это просто пара X-Account-Id /
 * X-Partner-Id, выбираемая через дев-переключатель. После регистрации
 * аккаунта или одобрения заявки сюда автоматически складываются новые id.
 */
@Injectable({ providedIn: 'root' })
export class IdentityService {
  private readonly state = signal<PartnerIdentity>(this.restore());
  readonly identities = signal<PartnerIdentity[]>(DEMO_IDENTITIES);

  readonly current = this.state.asReadonly();
  readonly accountId = computed(() => this.state().account_id);
  readonly partnerId = computed(() => this.state().partner_id);

  set(identity: PartnerIdentity): void {
    this.state.set(identity);
    this.persist();
  }

  setAccountId(accountId: string | null): void {
    this.state.update(s => ({ ...s, account_id: accountId }));
    this.persist();
  }

  setPartnerId(partnerId: string | null): void {
    this.state.update(s => ({ ...s, partner_id: partnerId }));
    this.persist();
  }

  setLabel(label: string): void {
    this.state.update(s => ({ ...s, label }));
    this.persist();
  }

  clear(): void {
    this.state.set({ account_id: null, partner_id: null, label: 'Гость' });
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

  private restore(): PartnerIdentity {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw) as PartnerIdentity;
      }
    } catch {
      /* no-op */
    }
    return DEMO_IDENTITIES[0];
  }
}
