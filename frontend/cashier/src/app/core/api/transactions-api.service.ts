import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { TransactionRead } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class TransactionsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  listPartner(limit = 50): Observable<TransactionRead[]> {
    const params = new HttpParams().set('limit', String(limit));
    return this.http.get<TransactionRead[]>(
      `${this.base}/partner/transactions`,
      { params },
    );
  }
}
