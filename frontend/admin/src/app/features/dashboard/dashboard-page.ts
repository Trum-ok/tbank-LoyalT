import { Component, computed, inject, signal } from '@angular/core';
import {
  AdminDailyCount,
  AdminPlatformOverview,
  AdminTopPartner,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { MetricsApi } from '../../core/api/metrics-api.service';
import {
  formatNumber,
  partnerCategoryLabel,
  partnerStatusLabel,
} from '../../core/format';

interface RangeOption {
  value: number | null;
  label: string;
}

interface Bar {
  label: string;
  value: number;
  ratio: number;
}

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private readonly metricsApi = inject(MetricsApi);

  readonly formatNumber = formatNumber;
  readonly partnerStatusLabel = partnerStatusLabel;
  readonly partnerCategoryLabel = partnerCategoryLabel;

  readonly ranges: RangeOption[] = [
    { value: 7, label: '7 дней' },
    { value: 30, label: '30 дней' },
    { value: 90, label: '90 дней' },
    { value: null, label: 'Всё время' },
  ];

  readonly loading = signal(true);
  readonly range = signal<number | null>(30);

  readonly overview = signal<AdminPlatformOverview | null>(null);
  readonly topPartners = signal<AdminTopPartner[]>([]);
  readonly newCustomers = signal<AdminDailyCount[]>([]);
  readonly newPartners = signal<AdminDailyCount[]>([]);

  readonly partners = computed(() => this.overview()?.partners ?? null);
  readonly customers = computed(() => this.overview()?.customers ?? null);
  readonly tx = computed(() => this.overview()?.transactions ?? null);

  readonly pointsTurnover = computed(() => {
    const t = this.tx();
    if (!t) return 0;
    return t.accruals_points + t.redemptions_points;
  });

  readonly statusRows = computed(() => {
    const p = this.partners();
    if (!p) return [];
    return Object.entries(p.by_status).map(([status, count]) => ({
      status,
      label: this.partnerStatusLabel(status),
      count,
    }));
  });

  readonly categoryRows = computed(() => {
    const p = this.partners();
    if (!p) return [];
    const max = Math.max(...Object.values(p.by_category), 1);
    return Object.entries(p.by_category)
      .map(([code, count]) => ({
        code,
        label: this.partnerCategoryLabel(code),
        count,
        ratio: count / max,
      }))
      .sort((a, b) => b.count - a.count);
  });

  readonly customersChart = computed(() => this.toBars(this.newCustomers()));
  readonly partnersChart = computed(() => this.toBars(this.newPartners()));

  constructor() {
    this.reload();
  }

  setRange(value: number | null): void {
    if (this.range() === value) return;
    this.range.set(value);
    this.reload();
  }

  private toBars(rows: AdminDailyCount[]): { bars: Bar[]; total: number } {
    const max = Math.max(...rows.map(r => r.count), 1);
    const bars = rows.map(r => ({
      label: this.dayLabel(r.day),
      value: r.count,
      ratio: r.count / max,
    }));
    const total = rows.reduce((acc, r) => acc + r.count, 0);
    return { bars, total };
  }

  xticks(bars: Bar[]): string[] {
    if (bars.length === 0) return [];
    if (bars.length <= 2) return bars.map(b => b.label);
    const mid = Math.floor((bars.length - 1) / 2);
    return [bars[0].label, bars[mid].label, bars[bars.length - 1].label];
  }

  private reload(): void {
    this.loading.set(true);
    const days = this.range();
    const histDays = days ?? 90;
    forkJoin({
      overview: this.metricsApi.overview().pipe(catchError(() => of(null))),
      top: this.metricsApi
        .topPartners({ limit: 10, days: days ?? undefined })
        .pipe(catchError(() => of([] as AdminTopPartner[]))),
      newCustomers: this.metricsApi
        .newCustomers(histDays)
        .pipe(catchError(() => of([] as AdminDailyCount[]))),
      newPartners: this.metricsApi
        .newPartners(histDays)
        .pipe(catchError(() => of([] as AdminDailyCount[]))),
      txPeriod: this.metricsApi
        .transactions(days ?? undefined)
        .pipe(catchError(() => of(null))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ overview, top, newCustomers, newPartners, txPeriod }) => {
        if (overview && txPeriod) {
          this.overview.set({ ...overview, transactions: txPeriod });
        } else {
          this.overview.set(overview);
        }
        this.topPartners.set(top);
        this.newCustomers.set(newCustomers);
        this.newPartners.set(newPartners);
      });
  }

  private dayLabel(key: string): string {
    const d = new Date(key);
    if (Number.isNaN(d.valueOf())) return key;
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
    }).format(d);
  }
}
