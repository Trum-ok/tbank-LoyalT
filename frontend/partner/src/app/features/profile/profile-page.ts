import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  AccountRead,
  PartnerCategory,
  PartnerRead,
  PartnerUpdate,
} from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { AccountsApi } from '../../core/api/accounts-api.service';
import { PartnerApi } from '../../core/api/partner-api.service';
import {
  formatDateTime,
  partnerCategoriesLabel,
  partnerStatusLabel,
} from '../../core/format';

const CATEGORIES: { code: PartnerCategory; label: string }[] = [
  { code: 'food', label: 'Кафе и еда' },
  { code: 'beauty', label: 'Красота' },
  { code: 'retail', label: 'Магазины' },
  { code: 'services', label: 'Услуги' },
  { code: 'entertainment', label: 'Развлечения' },
];
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
  readonly partnerCategoriesLabel = partnerCategoriesLabel;
  readonly partnerStatusLabel = partnerStatusLabel;
  readonly categories = CATEGORIES;

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly uploadingLogo = signal(false);
  readonly error = signal<string | null>(null);

  // Должно совпадать с PARTNER_LOGO_MAX_BYTES на бэкенде (2 МБ).
  private readonly logoMaxBytes = 2 * 1024 * 1024;
  private readonly logoAccept = [
    'image/png',
    'image/svg+xml',
    'image/jpeg',
    'image/webp',
  ];
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
            categories: [...p.categories],
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

  isCategorySelected(code: PartnerCategory): boolean {
    return (this.form().categories ?? []).includes(code);
  }

  toggleCategory(code: PartnerCategory): void {
    this.form.update(f => {
      const current = f.categories ?? [];
      const has = current.includes(code);
      const categories = has
        ? current.filter(c => c !== code)
        : [...current, code];
      // Минимум одна категория — не даём снять последнюю.
      return { ...f, categories: categories.length ? categories : current };
    });
  }

  onLogoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    if (!this.logoAccept.includes(file.type)) {
      this.notify.error('Поддерживаются только PNG, SVG, JPEG и WebP');
      input.value = '';
      return;
    }
    if (file.size > this.logoMaxBytes) {
      this.notify.error('Файл больше 2 МБ');
      input.value = '';
      return;
    }

    this.uploadingLogo.set(true);
    this.error.set(null);
    this.partnerApi
      .uploadLogo(file)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось загрузить логотип';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => {
          this.uploadingLogo.set(false);
          input.value = '';
        }),
      )
      .subscribe(p => {
        if (p) {
          this.partner.set(p);
          this.form.update(f => ({ ...f, logo_url: p.logo_url ?? '' }));
          this.notify.success('Логотип обновлён');
        }
      });
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
