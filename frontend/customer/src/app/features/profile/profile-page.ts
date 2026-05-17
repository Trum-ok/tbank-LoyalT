import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TuiDay } from '@taiga-ui/cdk';
import { TuiButton } from '@taiga-ui/core';
import { TuiInputDate } from '@taiga-ui/kit';
import { catchError, finalize, of } from 'rxjs';

import { ProfileApi } from '../../core/api/profile-api.service';
import { NotifyService } from '../../core/notify.service';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [ReactiveFormsModule, TuiInputDate, TuiButton],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
})
export class ProfilePage {
  private readonly profileApi = inject(ProfileApi);
  private readonly notify = inject(NotifyService);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly birthdayControl = new FormControl<TuiDay | null>(null);
  readonly maxDate = TuiDay.currentLocal();

  constructor() {
    this.profileApi
      .get()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (profile: { birthday?: string | null }) => {
          this.birthdayControl.setValue(
            profile.birthday ? TuiDay.jsonParse(profile.birthday) : null,
          );
        },
        error: () => {
          this.birthdayControl.setValue(null);
        },
      });
  }

  save(): void {
    this.saving.set(true);

    const birthday = this.birthdayControl.value?.toJSON() ?? null;

    this.profileApi
      .update({ birthday })
      .pipe(
        catchError((err: { error?: { detail?: string } }) => {
          this.notify.error(err?.error?.detail ?? 'Не удалось сохранить');
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe((result: { birthday?: string | null } | null) => {
        if (result) {
          this.birthdayControl.setValue(
            result.birthday ? TuiDay.jsonParse(result.birthday) : null,
          );
          this.notify.success('Профиль сохранён');
        }
      });
  }
}
