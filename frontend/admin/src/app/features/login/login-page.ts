import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AdminRead } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { AdminIdentityService } from '../../core/admin-identity.service';
import { AdminsApi } from '../../core/api/admins-api.service';
import { NotifyService } from '../../core/notify.service';

type Mode = 'existing' | 'bootstrap';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
})
export class LoginPage {
  private readonly adminsApi = inject(AdminsApi);
  private readonly identity = inject(AdminIdentityService);
  private readonly notify = inject(NotifyService);
  private readonly router = inject(Router);

  readonly mode = signal<Mode>('existing');
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly adminId = signal('');
  readonly email = signal('');
  readonly fullName = signal('');

  setMode(m: Mode): void {
    this.mode.set(m);
    this.error.set(null);
  }

  /** Вход по существующему X-Admin-Id: ставим личность и проверяем через
   *  /admins/me (интерцептор уже подложит заголовок). */
  enterExisting(): void {
    const id = this.adminId().trim();
    if (!id) {
      this.error.set('Укажите ID администратора');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.identity.set({ admin_id: id, email: null, label: 'Проверка…' });
    this.adminsApi
      .me()
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(admin => {
        if (!admin) {
          this.identity.clear();
          this.error.set('Администратор не найден или неактивен');
          return;
        }
        this.applyIdentity(admin);
      });
  }

  /** Bootstrap первого администратора: POST /admins без заголовка работает
   *  только при пустой таблице. */
  createBootstrap(): void {
    const email = this.email().trim();
    if (!email) {
      this.error.set('Укажите email');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.adminsApi
      .create({ email, full_name: this.fullName().trim() || null })
      .pipe(
        catchError((err: { status?: number }) => {
          if (err?.status === 401 || err?.status === 403) {
            this.error.set(
              'Администраторы уже есть. Войдите по существующему ID.',
            );
          } else {
            this.error.set('Не удалось создать администратора');
          }
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(admin => {
        if (admin) {
          this.applyIdentity(admin);
        }
      });
  }

  private applyIdentity(admin: AdminRead): void {
    this.identity.set({
      admin_id: admin.id,
      email: admin.email,
      label: admin.full_name || admin.email,
    });
    this.notify.success(`Вы вошли как ${admin.full_name || admin.email}`);
    this.router.navigate(['/dashboard']);
  }
}
