import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { TransactionRead } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

export interface PartnerTransactionsParams {
  program_id?: string | null;
  limit?: number;
  offset?: number;
}

@Injectable({ providedIn: 'root' })
export class TransactionsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  listPartner(
    params: PartnerTransactionsParams = {},
  ): Observable<TransactionRead[]> {
    let p = new HttpParams();
    if (params.program_id) p = p.set('program_id', params.program_id);
    if (params.limit !== undefined) p = p.set('limit', String(params.limit));
    if (params.offset !== undefined) p = p.set('offset', String(params.offset));
    return this.http.get<TransactionRead[]>(`${this.base}/partner/transactions`, {
      params: p,
    });
  }
}
