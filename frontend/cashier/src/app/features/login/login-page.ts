import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, of } from 'rxjs';

import { StaffApi } from '../../core/api/staff-api.service';
import { CashierIdentityService } from '../../core/cashier-identity.service';
import { NotifyService } from '../../core/notify.service';

const PIN_MAX = 8;

@Component({
  selector: 'app-login-page',
  standalone: true,
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
})
export class LoginPage {
  private readonly staffApi = inject(StaffApi);
  private readonly identity = inject(CashierIdentityService);
  private readonly notify = inject(NotifyService);
  private readonly router = inject(Router);

  readonly loginCode = signal('');
  readonly pin = signal('');
  readonly loading = signal(false);

  readonly keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'];
  readonly pinDots = computed(() => this.pin().length);
  readonly canSubmit = computed(
    () => this.loginCode().trim().length >= 3 && this.pin().length >= 4,
  );

  setCode(value: string): void {
    this.loginCode.set(value.toUpperCase());
  }

  press(key: string): void {
    if (key === '') return;
    if (key === '⌫') {
      this.pin.update(p => p.slice(0, -1));
      return;
    }
    this.pin.update(p => (p.length >= PIN_MAX ? p : p + key));
  }

  submit(): void {
    if (!this.canSubmit() || this.loading()) return;
    this.loading.set(true);
    this.staffApi
      .login({ login_code: this.loginCode().trim(), pin: this.pin() })
      .pipe(
        catchError(err => {
          const msg =
            err?.status === 403
              ? 'Неверный код точки или PIN'
              : err?.error?.detail ?? 'Не удалось войти';
          this.notify.error(msg);
          this.pin.set('');
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(session => {
        if (session) {
          this.identity.set(session);
          this.notify.success(`Смена открыта · ${session.partner_name}`);
          void this.router.navigate(['/pos']);
        }
      });
  }
}
