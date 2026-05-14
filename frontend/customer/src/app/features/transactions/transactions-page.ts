import { Component, computed, inject, signal } from '@angular/core';
import { TuiLoader } from '@taiga-ui/core';
import { TransactionRead } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { TransactionsApi } from '../../core/api/transactions-api.service';
import { formatDateTime, formatPoints } from '../../core/format';

interface TransactionGroup {
  label: string;
  items: TransactionRead[];
}

const MONTHS = [
  'январь',
  'февраль',
  'март',
  'апрель',
  'май',
  'июнь',
  'июль',
  'август',
  'сентябрь',
  'октябрь',
  'ноябрь',
  'декабрь',
];

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function groupTransactions(rows: TransactionRead[]): TransactionGroup[] {
  if (rows.length === 0) return [];
  const now = new Date();
  const todayMs = startOfDay(now);
  const yesterdayMs = todayMs - 24 * 60 * 60 * 1000;
  const groups = new Map<string, TransactionGroup>();
  for (const tx of rows) {
    const d = new Date(tx.created_at);
    const dayMs = startOfDay(d);
    let key: string;
    let label: string;
    if (dayMs === todayMs) {
      key = 'today';
      label = 'Сегодня';
    } else if (dayMs === yesterdayMs) {
      key = 'yesterday';
      label = 'Вчера';
    } else {
      key = `${d.getFullYear()}-${d.getMonth()}`;
      label =
        d.getFullYear() === now.getFullYear()
          ? MONTHS[d.getMonth()]
          : `${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
      label = label[0].toUpperCase() + label.slice(1);
    }
    if (!groups.has(key)) {
      groups.set(key, { label, items: [] });
    }
    groups.get(key)!.items.push(tx);
  }
  return [...groups.values()];
}

@Component({
  selector: 'app-transactions-page',
  standalone: true,
  imports: [TuiLoader],
  templateUrl: './transactions-page.html',
  styleUrl: './transactions-page.scss',
})
export class TransactionsPage {
  private readonly api = inject(TransactionsApi);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly transactions = signal<TransactionRead[]>([]);
  readonly groups = computed(() => groupTransactions(this.transactions()));

  readonly formatDateTime = formatDateTime;
  readonly formatPoints = formatPoints;

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .list()
      .pipe(
        catchError(err => {
          this.error.set(err?.message ?? 'Не удалось загрузить историю');
          return of([] as TransactionRead[]);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.transactions.set(rows));
  }

  typeLabel(t: TransactionRead): string {
    switch (t.type) {
      case 'accrual':
        return 'Начисление';
      case 'redemption':
        return 'Списание';
      case 'reversal':
        return 'Отмена';
    }
  }

  pointsDisplay(t: TransactionRead): string {
    if (t.type === 'redemption') return formatPoints(-t.points, true);
    return formatPoints(t.points, true);
  }
}
