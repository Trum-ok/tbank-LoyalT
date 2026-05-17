import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { catchError, finalize, of } from 'rxjs';

import { ProfileApi } from '../../core/api/profile-api.service';
import { NotifyService } from '../../core/notify.service';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
})
export class ProfilePage {
  private readonly profileApi = inject(ProfileApi);
  private readonly notify = inject(NotifyService);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly birthday = signal<string>('');
  readonly error = signal<string | null>(null);

  constructor() {
    this.profileApi
      .get()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: profile => {
          this.birthday.set(profile.birthday ?? '');
        },
        error: () => {
          this.birthday.set('');
        },
      });
  }

  save(): void {
    this.saving.set(true);
    this.error.set(null);

    const birthdayValue = this.birthday();

    this.profileApi
      .update({ birthday: birthdayValue || null })
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось сохранить';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(result => {
        if (result) {
          this.birthday.set(result.birthday ?? '');
          this.notify.success('Профиль сохранён');
        }
      });
  }
}
