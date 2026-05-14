import { Component, computed, inject, signal } from '@angular/core';
import { TuiLoader } from '@taiga-ui/core';
import { NotificationRead } from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { NotificationsApi } from '../../core/api/notifications-api.service';
import { formatDateTime } from '../../core/format';

@Component({
  selector: 'app-notifications-page',
  standalone: true,
  imports: [TuiLoader],
  templateUrl: './notifications-page.html',
  styleUrl: './notifications-page.scss',
})
export class NotificationsPage {
  private readonly api = inject(NotificationsApi);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly notifications = signal<NotificationRead[]>([]);
  readonly markingId = signal<string | null>(null);
  readonly markingAll = signal(false);

  readonly unread = computed(() => this.notifications().filter(n => !n.is_read));
  readonly read = computed(() => this.notifications().filter(n => n.is_read));

  readonly formatDateTime = formatDateTime;

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .list(false)
      .pipe(
        catchError(err => {
          this.error.set(err?.message ?? 'Не удалось загрузить уведомления');
          return of([] as NotificationRead[]);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.notifications.set(rows));
  }

  markRead(n: NotificationRead): void {
    if (n.is_read || this.markingId() === n.id) return;
    this.markingId.set(n.id);
    this.api
      .markRead(n.id)
      .pipe(finalize(() => this.markingId.set(null)))
      .subscribe({
        next: updated => {
          this.notifications.update(rows =>
            rows.map(r => (r.id === updated.id ? updated : r)),
          );
        },
      });
  }

  markAllRead(): void {
    const unread = this.unread();
    if (unread.length === 0 || this.markingAll()) return;
    this.markingAll.set(true);
    forkJoin(unread.map(n => this.api.markRead(n.id).pipe(catchError(() => of(null)))))
      .pipe(finalize(() => this.markingAll.set(false)))
      .subscribe(updated => {
        const map = new Map<string, NotificationRead>();
        for (const u of updated) {
          if (u) map.set(u.id, u);
        }
        this.notifications.update(rows =>
          rows.map(r => map.get(r.id) ?? r),
        );
      });
  }
}
