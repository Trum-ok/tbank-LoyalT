import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  ProgramRead,
  TransactionRead,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { PartnerApi } from '../../core/api/partner-api.service';
import { ProgramsApi } from '../../core/api/programs-api.service';
import { TransactionsApi } from '../../core/api/transactions-api.service';
import {
  formatAmount,
  formatDateTime,
  programStatusLabel,
  programTypeLabel,
  transactionTypeLabel,
} from '../../core/format';
import { IdentityService } from '../../core/identity.service';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private readonly partnerApi = inject(PartnerApi);
  private readonly programsApi = inject(ProgramsApi);
  private readonly txApi = inject(TransactionsApi);
  protected readonly identity = inject(IdentityService);

  readonly formatAmount = formatAmount;
  readonly formatDateTime = formatDateTime;
  readonly programTypeLabel = programTypeLabel;
  readonly programStatusLabel = programStatusLabel;
  readonly transactionTypeLabel = transactionTypeLabel;

  readonly loading = signal(true);
  readonly partnerName = signal<string | null>(null);
  readonly partnerStatus = signal<string | null>(null);
  readonly programs = signal<ProgramRead[]>([]);
  readonly transactions = signal<TransactionRead[]>([]);
  readonly hasAccount = computed(() => this.identity.accountId() !== null);
  readonly hasPartner = computed(() => this.identity.partnerId() !== null);

  readonly stats = computed(() => {
    const txs = this.transactions();
    const validTx = txs.filter(t => !t.is_reversed);
    const customers = new Set(validTx.map(t => t.customer_id));
    const accrued = validTx
      .filter(t => t.type === 'accrual')
      .reduce((sum, t) => sum + t.points, 0);
    const redeemed = validTx
      .filter(t => t.type === 'redemption')
      .reduce((sum, t) => sum + Math.abs(t.points), 0);
    const purchaseTotal = validTx
      .filter(t => t.purchase_amount !== null)
      .reduce((sum, t) => sum + Number(t.purchase_amount), 0);
    const averageCheck = validTx.length > 0 ? purchaseTotal / validTx.length : 0;

    return {
      customers: customers.size,
      accrued,
      redeemed,
      averageCheck,
      programs: this.programs().length,
      published: this.programs().filter(p => p.status === 'published').length,
    };
  });

  readonly daySeries = computed(() => {
    const buckets = new Map<string, number>();
    const today = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      buckets.set(this.dateKey(d), 0);
    }
    for (const tx of this.transactions()) {
      if (tx.type !== 'accrual' || tx.is_reversed) continue;
      const key = this.dateKey(new Date(tx.created_at));
      if (buckets.has(key)) {
        buckets.set(key, (buckets.get(key) ?? 0) + tx.points);
      }
    }
    const max = Math.max(1, ...Array.from(buckets.values()));
    return Array.from(buckets.entries()).map(([day, value]) => ({
      day,
      value,
      ratio: value / max,
      label: this.shortDayLabel(day),
    }));
  });

  readonly recent = computed(() => this.transactions().slice(0, 6));

  readonly topPrograms = computed(() => {
    const totals = new Map<string, number>();
    for (const tx of this.transactions()) {
      if (tx.type !== 'accrual' || tx.is_reversed) continue;
      totals.set(tx.program_id, (totals.get(tx.program_id) ?? 0) + tx.points);
    }
    return this.programs()
      .map(p => ({
        program: p,
        accrued: totals.get(p.id) ?? 0,
      }))
      .sort((a, b) => b.accrued - a.accrued)
      .slice(0, 4);
  });

  constructor() {
    this.bootstrap();
  }

  private bootstrap(): void {
    forkJoin({
      partner: this.partnerApi.me().pipe(catchError(() => of(null))),
      programs: this.programsApi
        .list()
        .pipe(catchError(() => of([] as ProgramRead[]))),
      transactions: this.txApi
        .listPartner({ limit: 200 })
        .pipe(catchError(() => of([] as TransactionRead[]))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ partner, programs, transactions }) => {
        this.partnerName.set(partner?.name ?? null);
        this.partnerStatus.set(partner?.status ?? null);
        this.programs.set(programs);
        this.transactions.set(transactions);
      });
  }

  private dateKey(d: Date): string {
    return `${d.getFullYear()}-${(d.getMonth() + 1)
      .toString()
      .padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
  }

  private shortDayLabel(key: string): string {
    const d = new Date(key);
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
    }).format(d);
  }
}
