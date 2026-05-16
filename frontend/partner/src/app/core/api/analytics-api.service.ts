import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { AnalyticsPeriod, AnalyticsRead } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class AnalyticsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  partner(period: AnalyticsPeriod): Observable<AnalyticsRead> {
    const params = new HttpParams().set('period', period);
    return this.http.get<AnalyticsRead>(`${this.base}/partner/analytics`, {
      params,
    });
  }
}
