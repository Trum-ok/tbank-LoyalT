import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApplicationRead, ApplicationStatus } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { ModerationApi } from '../../core/api/moderation-api.service';
import {
  applicationStatusLabel,
  formatDateTime,
  partnerCategoriesLabel,
} from '../../core/format';
import { NotifyService } from '../../core/notify.service';

type StatusFilter = ApplicationStatus | 'all';

interface FilterOption {
  value: StatusFilter;
  label: string;
}

@Component({
  selector: 'app-moderation-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './moderation-page.html',
  styleUrl: './moderation-page.scss',
})
export class ModerationPage {
  private readonly api = inject(ModerationApi);
  private readonly notify = inject(NotifyService);

  readonly applicationStatusLabel = applicationStatusLabel;
  readonly partnerCategoriesLabel = partnerCategoriesLabel;
  readonly formatDateTime = formatDateTime;

  readonly filters: FilterOption[] = [
    { value: 'pending', label: 'На модерации' },
    { value: 'approved', label: 'Одобренные' },
    { value: 'rejected', label: 'Отклонённые' },
    { value: 'all', label: 'Все' },
  ];

  readonly loading = signal(true);
  readonly filter = signal<StatusFilter>('pending');
  readonly items = signal<ApplicationRead[]>([]);
  readonly expandedId = signal<string | null>(null);
  readonly comment = signal('');
  readonly acting = signal<string | null>(null);

  readonly pendingCount = computed(
    () => this.items().filter(a => a.status === 'pending').length,
  );

  constructor() {
    this.reload();
  }

  setFilter(value: StatusFilter): void {
    if (this.filter() === value) return;
    this.filter.set(value);
    this.expandedId.set(null);
    this.reload();
  }

  toggle(id: string): void {
    this.expandedId.set(this.expandedId() === id ? null : id);
    this.comment.set('');
  }

  approve(app: ApplicationRead): void {
    this.acting.set(app.id);
    this.api
      .approve(app.id, { comment: this.comment().trim() || null })
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось одобрить заявку');
          return of(null);
        }),
        finalize(() => this.acting.set(null)),
      )
      .subscribe(partner => {
        if (partner) {
          this.notify.success(`Партнёр «${partner.name}» создан`);
          this.expandedId.set(null);
          this.reload();
        }
      });
  }

  reject(app: ApplicationRead): void {
    const comment = this.comment().trim();
    if (!comment) {
      this.notify.error('Укажите причину отклонения в комментарии');
      return;
    }
    this.acting.set(app.id);
    this.api
      .reject(app.id, { comment })
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось отклонить заявку');
          return of(null);
        }),
        finalize(() => this.acting.set(null)),
      )
      .subscribe(res => {
        if (res) {
          this.notify.success('Заявка отклонена');
          this.expandedId.set(null);
          this.reload();
        }
      });
  }

  private reload(): void {
    this.loading.set(true);
    const f = this.filter();
    this.api
      .listApplications({ status: f === 'all' ? null : f, limit: 100 })
      .pipe(
        catchError(() => of([] as ApplicationRead[])),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(list => this.items.set(list));
  }
}
