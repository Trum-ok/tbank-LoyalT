import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  AnalyticsPeriod,
  AnalyticsRead,
  ProgramRead,
  TransactionRead,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { AnalyticsApi } from '../../core/api/analytics-api.service';
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

interface PeriodOption {
  value: AnalyticsPeriod;
  label: string;
}

type DashboardTab = 'overview' | 'engagement' | 'retention';

interface TabOption {
  value: DashboardTab;
  label: string;
}

const DOW_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

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
  private readonly analyticsApi = inject(AnalyticsApi);
  protected readonly identity = inject(IdentityService);

  readonly formatAmount = formatAmount;
  readonly formatDateTime = formatDateTime;
  readonly programTypeLabel = programTypeLabel;
  readonly programStatusLabel = programStatusLabel;
  readonly transactionTypeLabel = transactionTypeLabel;

  readonly periods: PeriodOption[] = [
    { value: '1d', label: '1д' },
    { value: '7d', label: '7д' },
    { value: '14d', label: '14д' },
    { value: '30d', label: '30д' },
    { value: '90d', label: '90д' },
    { value: 'all', label: 'Всё время' },
  ];

  readonly tabs: TabOption[] = [
    { value: 'overview', label: 'Обзор' },
    { value: 'engagement', label: 'Вовлечённость' },
    { value: 'retention', label: 'Удержание' },
  ];

  readonly loading = signal(true);
  readonly analyticsLoading = signal(true);
  readonly tab = signal<DashboardTab>('overview');
  readonly period = signal<AnalyticsPeriod>('30d');
  readonly partnerName = signal<string | null>(null);
  readonly programs = signal<ProgramRead[]>([]);
  readonly transactions = signal<TransactionRead[]>([]);
  readonly analytics = signal<AnalyticsRead | null>(null);

  readonly hasAccount = computed(() => this.identity.accountId() !== null);
  readonly hasPartner = computed(() => this.identity.partnerId() !== null);

  readonly summary = computed(() => this.analytics()?.summary ?? null);
  readonly stickiness = computed(() => this.analytics()?.stickiness ?? null);
  readonly retention = computed(() => this.analytics()?.retention ?? null);

  readonly publishedCount = computed(
    () => this.programs().filter(p => p.status === 'published').length,
  );

  // Гистограмма «новые юзеры по дням».
  readonly newUsersSeries = computed(() => {
    const rows = this.analytics()?.new_users_by_day ?? [];
    const max = Math.max(1, ...rows.map(r => r.count));
    return rows.map(r => ({
      label: this.dayLabel(r.date),
      value: r.count,
      ratio: r.count / max,
      title: `${r.date} · ${r.count} новых`,
    }));
  });

  // Гистограмма «покупки / юзер по дням».
  readonly purchasesSeries = computed(() => {
    const rows = this.analytics()?.purchases_per_user_by_day ?? [];
    const max = Math.max(0.0001, ...rows.map(r => r.ratio));
    return rows.map(r => ({
      label: this.dayLabel(r.date),
      value: r.ratio,
      ratio: r.ratio / max,
      title: `${r.date} · ${r.ratio} (${r.purchases} покупок / ${r.users} юзеров)`,
    }));
  });

  // Кривая retention для SVG-полилинии (viewBox 100×100).
  readonly retentionPath = computed(() => {
    const curve = this.analytics()?.retention.curve ?? [];
    if (curve.length < 2) return null;
    const n = curve.length - 1;
    const pts = curve
      .map((p, i) => {
        const x = (i / n) * 100;
        const y = 100 - p.retention * 100;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
    const area = `0,100 ${pts} 100,100`;
    const median = this.analytics()?.retention.median_churn_day ?? null;
    const medianX = median !== null ? (median / n) * 100 : null;
    return { line: pts, area, medianX, lastDay: curve[curve.length - 1].day };
  });

  readonly heatmap = computed(() => {
    const hm = this.analytics()?.heatmap;
    if (!hm) return null;
    const rows = DOW_LABELS.map((label, dow) => ({
      label,
      cells: Array.from({ length: 24 }, (_, hour) => {
        const cell = hm.cells.find(c => c.dow === dow && c.hour === hour);
        const count = cell?.count ?? 0;
        return {
          hour,
          count,
          intensity: hm.max > 0 ? count / hm.max : 0,
        };
      }),
    }));
    return { rows, max: hm.max, hours: Array.from({ length: 24 }, (_, h) => h) };
  });

  readonly recent = computed(() => this.transactions().slice(0, 6));

  readonly topPrograms = computed(() => {
    const totals = new Map<string, number>();
    for (const tx of this.transactions()) {
      if (tx.type !== 'accrual' || tx.is_reversed) continue;
      totals.set(tx.program_id, (totals.get(tx.program_id) ?? 0) + tx.points);
    }
    return this.programs()
      .map(p => ({ program: p, accrued: totals.get(p.id) ?? 0 }))
      .sort((a, b) => b.accrued - a.accrued)
      .slice(0, 4);
  });

  constructor() {
    this.bootstrap();
  }

  setPeriod(p: AnalyticsPeriod): void {
    if (this.period() === p) return;
    this.period.set(p);
    this.loadAnalytics();
  }

  setTab(t: DashboardTab): void {
    this.tab.set(t);
  }

  pct(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${value}%`;
  }

  ret(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${(value * 100).toFixed(1)}%`;
  }

  private bootstrap(): void {
    if (this.identity.partnerId() === null) {
      this.loading.set(false);
      this.analyticsLoading.set(false);
      return;
    }
    forkJoin({
      partner: this.partnerApi.me().pipe(catchError(() => of(null))),
      programs: this.programsApi
        .list()
        .pipe(catchError(() => of([] as ProgramRead[]))),
      transactions: this.txApi
        .listPartner({ limit: 50 })
        .pipe(catchError(() => of([] as TransactionRead[]))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ partner, programs, transactions }) => {
        this.partnerName.set(partner?.name ?? null);
        this.programs.set(programs);
        this.transactions.set(transactions);
      });
    this.loadAnalytics();
  }

  private loadAnalytics(): void {
    this.analyticsLoading.set(true);
    this.analyticsApi
      .partner(this.period())
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.analyticsLoading.set(false)),
      )
      .subscribe(data => this.analytics.set(data));
  }

  private dayLabel(key: string): string {
    const d = new Date(key);
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
    }).format(d);
  }
}
