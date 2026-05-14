import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  ApplicationCreate,
  ApplicationRead,
  ApplicationUpdate,
  PartnerCategory,
} from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { AccountsApi } from '../../core/api/accounts-api.service';
import { ApplicationsApi } from '../../core/api/applications-api.service';
import { PartnerApi } from '../../core/api/partner-api.service';
import {
  applicationStatusLabel,
  formatDateTime,
  partnerCategoryLabel,
} from '../../core/format';
import { IdentityService } from '../../core/identity.service';
import { NotifyService } from '../../core/notify.service';

const CATEGORIES: { code: PartnerCategory; label: string }[] = [
  { code: 'food', label: 'Кафе и еда' },
  { code: 'beauty', label: 'Красота' },
  { code: 'retail', label: 'Магазины' },
  { code: 'services', label: 'Услуги' },
  { code: 'entertainment', label: 'Развлечения' },
];

interface AccountForm {
  email: string;
  full_name: string;
  phone: string;
}

interface ApplicationForm {
  business_name: string;
  inn: string;
  category: PartnerCategory;
  contact_email: string;
  contact_phone: string;
  description: string;
}

@Component({
  selector: 'app-onboarding-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './onboarding-page.html',
  styleUrl: './onboarding-page.scss',
})
export class OnboardingPage {
  private readonly accountsApi = inject(AccountsApi);
  private readonly applicationsApi = inject(ApplicationsApi);
  private readonly partnerApi = inject(PartnerApi);
  protected readonly identity = inject(IdentityService);
  private readonly notify = inject(NotifyService);

  readonly categories = CATEGORIES;
  readonly partnerCategoryLabel = partnerCategoryLabel;
  readonly applicationStatusLabel = applicationStatusLabel;
  readonly formatDateTime = formatDateTime;

  readonly accountForm = signal<AccountForm>({
    email: '',
    full_name: '',
    phone: '',
  });
  readonly applicationForm = signal<ApplicationForm>({
    business_name: '',
    inn: '',
    category: 'food',
    contact_email: '',
    contact_phone: '',
    description: '',
  });

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly applications = signal<ApplicationRead[] | null>(null);
  readonly editingApplicationId = signal<string | null>(null);

  readonly hasAccount = computed(() => this.identity.accountId() !== null);
  readonly hasPartner = computed(() => this.identity.partnerId() !== null);

  readonly latestApp = computed(() => {
    const apps = this.applications();
    if (!apps || apps.length === 0) return null;
    return [...apps].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    )[0];
  });

  readonly pendingApp = computed(() => {
    const app = this.latestApp();
    return app && app.status === 'pending' ? app : null;
  });

  readonly isEditingApplication = computed(
    () => this.editingApplicationId() !== null,
  );

  constructor() {
    effect(() => {
      if (this.identity.accountId()) {
        this.refreshApplications();
        this.tryAttachPartner();
      } else {
        this.applications.set(null);
      }
    });
  }

  patchAccount<K extends keyof AccountForm>(key: K, value: AccountForm[K]): void {
    this.accountForm.update(f => ({ ...f, [key]: value }));
  }

  fillAccountDemo(): void {
    const suffix = Date.now().toString(36);
    this.accountForm.set({
      email: `demo.partner.${suffix}@example.com`,
      full_name: 'Иван Петров',
      phone: '+7 (912) 345-67-89',
    });
  }

  fillApplicationDemo(): void {
    const current = this.applicationForm();
    this.applicationForm.set({
      business_name: 'ООО «Кофейня Утро»',
      inn: '7708123456',
      category: 'food',
      contact_email: current.contact_email || 'contact@coffee-utro.ru',
      contact_phone: current.contact_phone || '+7 (495) 123-45-67',
      description:
        'Сеть кофеен в центре Москвы, специализируемся на спешелти-кофе и завтраках.',
    });
  }

  patchApplication<K extends keyof ApplicationForm>(
    key: K,
    value: ApplicationForm[K],
  ): void {
    this.applicationForm.update(f => ({ ...f, [key]: value }));
  }

  submitAccount(): void {
    const form = this.accountForm();
    if (!form.email) {
      this.error.set('Введите email');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.accountsApi
      .signup({
        email: form.email,
        full_name: form.full_name || null,
        phone: form.phone || null,
      })
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось создать аккаунт';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(account => {
        if (!account) return;
        this.identity.set({
          account_id: account.id,
          partner_id: null,
          label: account.full_name || account.email,
          is_demo: this.identity.isDemo(),
        });
        this.applicationForm.update(f => ({
          ...f,
          contact_email: account.email,
          contact_phone: account.phone ?? '',
        }));
        this.notify.success('Аккаунт создан, переходите ко 2 шагу');
      });
  }

  submitApplication(): void {
    const f = this.applicationForm();
    if (!f.business_name || !f.inn || !f.contact_email) {
      this.error.set('Заполните название, ИНН и контактный email');
      return;
    }

    const editingId = this.editingApplicationId();
    this.loading.set(true);
    this.error.set(null);

    if (editingId) {
      const patch: ApplicationUpdate = {
        business_name: f.business_name,
        inn: f.inn,
        category: f.category,
        contact_email: f.contact_email,
        contact_phone: f.contact_phone || null,
        description: f.description || null,
      };
      this.applicationsApi
        .updateMine(editingId, patch)
        .pipe(
          catchError(err => {
            const msg = err?.error?.detail ?? 'Не удалось сохранить изменения';
            this.error.set(msg);
            this.notify.error(msg);
            return of(null);
          }),
          finalize(() => this.loading.set(false)),
        )
        .subscribe(app => {
          if (app) {
            this.editingApplicationId.set(null);
            this.refreshApplications();
            this.notify.success('Заявка обновлена');
          }
        });
      return;
    }

    const body: ApplicationCreate = {
      business_name: f.business_name,
      inn: f.inn,
      category: f.category,
      contact_email: f.contact_email,
      contact_phone: f.contact_phone || null,
      description: f.description || null,
    };
    this.applicationsApi
      .submit(body)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось отправить заявку';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(app => {
        if (app) {
          this.refreshApplications();
          this.notify.success('Заявка отправлена на модерацию');
        }
      });
  }

  editApplication(app: ApplicationRead): void {
    this.applicationForm.set({
      business_name: app.business_name,
      inn: app.inn,
      category: app.category,
      contact_email: app.contact_email,
      contact_phone: app.contact_phone ?? '',
      description: app.description ?? '',
    });
    this.editingApplicationId.set(app.id);
    this.error.set(null);
  }

  cancelEdit(): void {
    this.editingApplicationId.set(null);
    this.error.set(null);
  }

  withdrawApplication(): void {
    if (!confirm('Отозвать заявку? Её можно будет подать заново.')) return;
    this.loading.set(true);
    this.error.set(null);
    this.applicationsApi
      .withdrawMine()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: () => {
          this.applicationForm.set({
            business_name: '',
            inn: '',
            category: 'food',
            contact_email: '',
            contact_phone: '',
            description: '',
          });
          this.editingApplicationId.set(null);
          this.refreshApplications();
          this.notify.success('Заявка отозвана');
        },
        error: err => {
          const msg = err?.error?.detail ?? 'Не удалось отозвать заявку';
          this.error.set(msg);
          this.notify.error(msg);
        },
      });
  }

  refreshApplications(): void {
    this.applicationsApi
      .listMine()
      .pipe(catchError(() => of([] as ApplicationRead[])))
      .subscribe(rows => this.applications.set(rows));
  }

  private tryAttachPartner(): void {
    if (this.identity.partnerId()) return;
    this.partnerApi
      .me()
      .pipe(catchError(() => of(null)))
      .subscribe(p => {
        if (p) {
          this.identity.set({
            account_id: this.identity.accountId(),
            partner_id: p.id,
            label: p.name,
            is_demo: this.identity.isDemo(),
          });
        }
      });
  }
}
