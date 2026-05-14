import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  ProgramRead,
  TransactionRead,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { ProgramsApi } from '../../core/api/programs-api.service';
import { TransactionsApi } from '../../core/api/transactions-api.service';
import {
  formatAmount,
  formatDateTime,
  transactionTypeLabel,
} from '../../core/format';

interface TxGroup {
  day: string;
  items: TransactionRead[];
}

@Component({
  selector: 'app-transactions-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './transactions-page.html',
  styleUrl: './transactions-page.scss',
})
export class TransactionsPage {
  private readonly txApi = inject(TransactionsApi);
  private readonly programsApi = inject(ProgramsApi);

  readonly formatDateTime = formatDateTime;
  readonly formatAmount = formatAmount;
  readonly transactionTypeLabel = transactionTypeLabel;

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly programs = signal<ProgramRead[]>([]);
  readonly transactions = signal<TransactionRead[]>([]);
  readonly programFilter = signal<string | null>(null);

  readonly summary = computed(() => {
    const all = this.transactions();
    const accrued = all
      .filter(t => t.type === 'accrual' && !t.is_reversed)
      .reduce((sum, t) => sum + t.points, 0);
    const redeemed = all
      .filter(t => t.type === 'redemption' && !t.is_reversed)
      .reduce((sum, t) => sum + Math.abs(t.points), 0);
    return {
      total: all.length,
      accrued,
      redeemed,
      reversals: all.filter(t => t.type === 'reversal').length,
    };
  });

  readonly groups = computed<TxGroup[]>(() => {
    const items = [...this.transactions()].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    );
    const map = new Map<string, TransactionRead[]>();
    for (const tx of items) {
      const day = this.dayKey(tx.created_at);
      const arr = map.get(day) ?? [];
      arr.push(tx);
      map.set(day, arr);
    }
    return Array.from(map.entries()).map(([day, items]) => ({ day, items }));
  });

  readonly programLabelByid = computed(() => {
    const m = new Map<string, string>();
    for (const p of this.programs()) m.set(p.id, p.name);
    return m;
  });

  constructor() {
    forkJoin({
      programs: this.programsApi.list().pipe(catchError(() => of([] as ProgramRead[]))),
      transactions: this.txApi
        .listPartner({ limit: 200 })
        .pipe(catchError(() => of([] as TransactionRead[]))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ programs, transactions }) => {
        this.programs.set(programs);
        this.transactions.set(transactions);
      });
  }

  setProgramFilter(value: string | null): void {
    this.programFilter.set(value);
    this.loadTransactions(value);
  }

  private loadTransactions(programId: string | null): void {
    this.loading.set(true);
    this.error.set(null);
    this.txApi
      .listPartner({ program_id: programId, limit: 200 })
      .pipe(
        catchError(err => {
          this.error.set(
            err?.error?.detail ?? 'Не удалось загрузить транзакции',
          );
          return of([] as TransactionRead[]);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.transactions.set(rows));
  }

  private dayKey(iso: string): string {
    const d = new Date(iso);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    const sameDay = (a: Date, b: Date) =>
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();

    if (sameDay(d, today)) return 'Сегодня';
    if (sameDay(d, yesterday)) return 'Вчера';

    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: 'long',
    }).format(d);
  }

  programName(id: string): string {
    return this.programLabelByid().get(id) ?? '—';
  }
}
