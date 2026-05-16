import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AccruePayload,
  EnrollmentLookup,
  PointsOperationResult,
  RedeemPayload,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class PointsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  lookup(enrollmentId: string): Observable<EnrollmentLookup> {
    return this.http.get<EnrollmentLookup>(
      `${this.base}/points/lookup/${enrollmentId}`,
    );
  }

  lookupByCode(code: string): Observable<EnrollmentLookup> {
    return this.http.get<EnrollmentLookup>(
      `${this.base}/points/lookup-code/${code}`,
    );
  }

  accrue(body: AccruePayload): Observable<PointsOperationResult> {
    return this.http.post<PointsOperationResult>(
      `${this.base}/points/accrue`,
      body,
    );
  }

  redeem(body: RedeemPayload): Observable<PointsOperationResult> {
    return this.http.post<PointsOperationResult>(
      `${this.base}/points/redeem`,
      body,
    );
  }

  reverse(
    transactionId: string,
    description?: string,
  ): Observable<PointsOperationResult> {
    return this.http.post<PointsOperationResult>(
      `${this.base}/points/transactions/${transactionId}/reverse`,
      { description: description ?? null },
    );
  }
}
