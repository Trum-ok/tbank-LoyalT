import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { StaffCreate, StaffRead } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { StaffApi } from '../../core/api/staff-api.service';
import { formatDateTime } from '../../core/format';
import { IdentityService } from '../../core/identity.service';
import { NotifyService } from '../../core/notify.service';

const EMPTY_FORM: StaffCreate = { name: '', login_code: '', pin: '' };

@Component({
  selector: 'app-staff-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './staff-page.html',
  styleUrl: './staff-page.scss',
})
export class StaffPage {
  private readonly staffApi = inject(StaffApi);
  private readonly identity = inject(IdentityService);
  private readonly notify = inject(NotifyService);

  readonly formatDateTime = formatDateTime;

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly staff = signal<StaffRead[]>([]);
  readonly form = signal<StaffCreate>({ ...EMPTY_FORM });

  readonly hasPartner = computed(() => this.identity.partnerId() !== null);

  constructor() {
    effect(() => {
      if (this.identity.accountId()) {
        this.reload();
      } else {
        this.staff.set([]);
        this.loading.set(false);
      }
    });
  }

  reload(): void {
    this.loading.set(true);
    this.error.set(null);
    this.staffApi
      .list()
      .pipe(
        catchError(() => of([] as StaffRead[])),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.staff.set(rows));
  }

  patch<K extends keyof StaffCreate>(key: K, value: StaffCreate[K]): void {
    this.form.update(f => ({ ...f, [key]: value }));
  }

  create(): void {
    const body = this.form();
    if (!body.name.trim() || !body.login_code.trim() || !body.pin.trim()) {
      this.notify.error('Заполните имя, код точки и PIN');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.staffApi
      .create({
        name: body.name.trim(),
        login_code: body.login_code.trim().toUpperCase(),
        pin: body.pin.trim(),
      })
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось создать кассира';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(created => {
        if (created) {
          this.staff.update(list => [created, ...list]);
          this.form.set({ ...EMPTY_FORM });
          this.notify.success('Кассир добавлен');
        }
      });
  }

  toggleActive(s: StaffRead): void {
    this.staffApi
      .update(s.id, { is_active: !s.is_active })
      .pipe(
        catchError(err => {
          this.notify.error(err?.error?.detail ?? 'Не удалось обновить');
          return of(null);
        }),
      )
      .subscribe(updated => {
        if (updated) {
          this.staff.update(list =>
            list.map(x => (x.id === updated.id ? updated : x)),
          );
        }
      });
  }

  resetPin(s: StaffRead): void {
    const pin = window.prompt(`Новый PIN для «${s.name}» (4–8 цифр)`);
    if (pin === null) return;
    if (!/^\d{4,8}$/.test(pin)) {
      this.notify.error('PIN — от 4 до 8 цифр');
      return;
    }
    this.staffApi
      .update(s.id, { pin })
      .pipe(
        catchError(err => {
          this.notify.error(err?.error?.detail ?? 'Не удалось сменить PIN');
          return of(null);
        }),
      )
      .subscribe(updated => {
        if (updated) this.notify.success('PIN обновлён');
      });
  }

  remove(s: StaffRead): void {
    if (!window.confirm(`Удалить кассира «${s.name}»?`)) return;
    this.staffApi
      .remove(s.id)
      .pipe(
        catchError(err => {
          this.notify.error(err?.error?.detail ?? 'Не удалось удалить');
          return of(null);
        }),
      )
      .subscribe(() => {
        this.staff.update(list => list.filter(x => x.id !== s.id));
        this.notify.success('Кассир удалён');
      });
  }
}
