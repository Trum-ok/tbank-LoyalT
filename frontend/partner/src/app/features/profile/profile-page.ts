import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  AccountRead,
  PartnerRead,
  PartnerUpdate,
} from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { AccountsApi } from '../../core/api/accounts-api.service';
import { PartnerApi } from '../../core/api/partner-api.service';
import {
  formatDateTime,
  partnerCategoryLabel,
} from '../../core/format';
import { IdentityService } from '../../core/identity.service';
import { NotifyService } from '../../core/notify.service';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
})
export class ProfilePage {
  private readonly partnerApi = inject(PartnerApi);
  private readonly accountsApi = inject(AccountsApi);
  private readonly identity = inject(IdentityService);
  private readonly notify = inject(NotifyService);

  readonly formatDateTime = formatDateTime;
  readonly partnerCategoryLabel = partnerCategoryLabel;

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly partner = signal<PartnerRead | null>(null);
  readonly account = signal<AccountRead | null>(null);

  readonly form = signal<PartnerUpdate>({});

  readonly accountId = computed(() => this.identity.accountId());

  constructor() {
    effect(() => {
      if (this.accountId()) {
        this.reload();
      } else {
        this.partner.set(null);
        this.account.set(null);
        this.loading.set(false);
      }
    });
  }

  reload(): void {
    this.loading.set(true);
    this.error.set(null);

    this.partnerApi
      .me()
      .pipe(catchError(() => of(null)))
      .subscribe(p => {
        this.partner.set(p);
        if (p) {
          this.form.set({
            name: p.name,
            logo_url: p.logo_url ?? '',
            brand_color: p.brand_color ?? '',
            contact_email: p.contact_email,
            contact_phone: p.contact_phone ?? '',
          });
        }
      });

    this.accountsApi
      .me()
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(a => this.account.set(a));
  }

  patch<K extends keyof PartnerUpdate>(key: K, value: PartnerUpdate[K]): void {
    this.form.update(f => ({ ...f, [key]: value }));
  }

  save(): void {
    const body = this.form();
    this.saving.set(true);
    this.error.set(null);
    this.partnerApi
      .updateMe(body)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось сохранить профиль';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(p => {
        if (p) {
          this.partner.set(p);
          this.identity.setLabel(p.name);
          this.notify.success('Профиль обновлён');
        }
      });
  }
}
