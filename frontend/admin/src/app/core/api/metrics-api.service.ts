import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AdminCustomersOverview,
  AdminDailyCount,
  AdminPartnersOverview,
  AdminPlatformOverview,
  AdminTopPartner,
  AdminTransactionsOverview,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { ADMIN_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class MetricsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(ADMIN_API_BASE);

  overview(): Observable<AdminPlatformOverview> {
    return this.http.get<AdminPlatformOverview>(`${this.base}/metrics/overview`);
  }

  partners(): Observable<AdminPartnersOverview> {
    return this.http.get<AdminPartnersOverview>(`${this.base}/metrics/partners`);
  }

  customers(): Observable<AdminCustomersOverview> {
    return this.http.get<AdminCustomersOverview>(
      `${this.base}/metrics/customers`,
    );
  }

  transactions(days?: number): Observable<AdminTransactionsOverview> {
    let params = new HttpParams();
    if (days) params = params.set('days', String(days));
    return this.http.get<AdminTransactionsOverview>(
      `${this.base}/metrics/transactions`,
      { params },
    );
  }

  topPartners(opts: { limit?: number; days?: number } = {}): Observable<
    AdminTopPartner[]
  > {
    let params = new HttpParams().set('limit', String(opts.limit ?? 10));
    if (opts.days) params = params.set('days', String(opts.days));
    return this.http.get<AdminTopPartner[]>(`${this.base}/metrics/top-partners`, {
      params,
    });
  }

  newCustomers(days = 30): Observable<AdminDailyCount[]> {
    const params = new HttpParams().set('days', String(days));
    return this.http.get<AdminDailyCount[]>(
      `${this.base}/metrics/new-customers`,
      { params },
    );
  }

  newPartners(days = 30): Observable<AdminDailyCount[]> {
    const params = new HttpParams().set('days', String(days));
    return this.http.get<AdminDailyCount[]>(
      `${this.base}/metrics/new-partners`,
      { params },
    );
  }
}
