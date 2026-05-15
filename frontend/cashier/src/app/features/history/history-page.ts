import { Component, inject, signal } from '@angular/core';
import { TransactionRead } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { PointsApi } from '../../core/api/points-api.service';
import { TransactionsApi } from '../../core/api/transactions-api.service';
import {
  formatDateTime,
  formatPoints,
  transactionTypeLabel,
} from '../../core/format';
import { NotifyService } from '../../core/notify.service';

@Component({
  selector: 'app-history-page',
  standalone: true,
  templateUrl: './history-page.html',
  styleUrl: './history-page.scss',
})
export class HistoryPage {
  private readonly txApi = inject(TransactionsApi);
  private readonly pointsApi = inject(PointsApi);
  private readonly notify = inject(NotifyService);

  readonly formatDateTime = formatDateTime;
  readonly formatPoints = formatPoints;
  readonly transactionTypeLabel = transactionTypeLabel;

  readonly loading = signal(true);
  readonly reversingId = signal<string | null>(null);
  readonly transactions = signal<TransactionRead[]>([]);

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.txApi
      .listPartner(50)
      .pipe(
        catchError(() => of([] as TransactionRead[])),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.transactions.set(rows));
  }

  canReverse(t: TransactionRead): boolean {
    return (
      !t.is_reversed &&
      (t.type === 'accrual' || t.type === 'redemption')
    );
  }

  reverse(t: TransactionRead): void {
    if (!this.canReverse(t) || this.reversingId()) return;
    if (!window.confirm('Отменить эту операцию?')) return;
    this.reversingId.set(t.id);
    this.pointsApi
      .reverse(t.id, 'Отмена с кассы')
      .pipe(
        catchError(err => {
          this.notify.error(
            err?.error?.detail ?? 'Не удалось отменить операцию',
          );
          return of(null);
        }),
        finalize(() => this.reversingId.set(null)),
      )
      .subscribe(res => {
        if (res) {
          this.notify.success('Операция отменена');
          this.reload();
        }
      });
  }
}
