import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PartnerRead, PartnerStatus } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { ModerationApi } from '../../core/api/moderation-api.service';
import {
  formatDate,
  partnerCategoryLabel,
  partnerStatusLabel,
} from '../../core/format';
import { NotifyService } from '../../core/notify.service';

type StatusFilter = PartnerStatus | 'all';

interface FilterOption {
  value: StatusFilter;
  label: string;
}

@Component({
  selector: 'app-partners-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './partners-page.html',
  styleUrl: './partners-page.scss',
})
export class PartnersPage {
  private readonly api = inject(ModerationApi);
  private readonly notify = inject(NotifyService);

  readonly partnerStatusLabel = partnerStatusLabel;
  readonly partnerCategoryLabel = partnerCategoryLabel;
  readonly formatDate = formatDate;

  readonly filters: FilterOption[] = [
    { value: 'all', label: 'Все' },
    { value: 'active', label: 'Активные' },
    { value: 'suspended', label: 'Приостановленные' },
    { value: 'blocked', label: 'Заблокированные' },
  ];

  readonly loading = signal(true);
  readonly filter = signal<StatusFilter>('all');
  readonly query = signal('');
  readonly items = signal<PartnerRead[]>([]);
  readonly acting = signal<string | null>(null);

  readonly visible = computed(() => {
    const q = this.query().trim().toLowerCase();
    if (!q) return this.items();
    return this.items().filter(
      p =>
        p.name.toLowerCase().includes(q) ||
        p.inn.includes(q) ||
        p.contact_email.toLowerCase().includes(q),
    );
  });

  constructor() {
    this.reload();
  }

  setFilter(value: StatusFilter): void {
    if (this.filter() === value) return;
    this.filter.set(value);
    this.reload();
  }

  suspend(p: PartnerRead): void {
    this.run(p.id, this.api.suspendPartner(p.id), 'Партнёр приостановлен');
  }

  block(p: PartnerRead): void {
    this.run(p.id, this.api.blockPartner(p.id), 'Партнёр заблокирован');
  }

  unblock(p: PartnerRead): void {
    this.run(p.id, this.api.unblockPartner(p.id), 'Партнёр разблокирован');
  }

  private run(
    id: string,
    obs: ReturnType<ModerationApi['suspendPartner']>,
    okMsg: string,
  ): void {
    this.acting.set(id);
    obs
      .pipe(
        catchError(() => {
          this.notify.error('Действие не выполнено');
          return of(null);
        }),
        finalize(() => this.acting.set(null)),
      )
      .subscribe(updated => {
        if (updated) {
          this.notify.success(okMsg);
          this.items.update(list =>
            list.map(p => (p.id === updated.id ? updated : p)),
          );
        }
      });
  }

  private reload(): void {
    this.loading.set(true);
    const f = this.filter();
    this.api
      .listPartners({ status: f === 'all' ? null : f, limit: 200 })
      .pipe(
        catchError(() => of([] as PartnerRead[])),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(list => this.items.set(list));
  }
}
