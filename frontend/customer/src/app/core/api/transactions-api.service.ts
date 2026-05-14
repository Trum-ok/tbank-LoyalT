import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { TransactionRead } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class TransactionsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  list(programId?: string): Observable<TransactionRead[]> {
    let params = new HttpParams();
    if (programId) {
      params = params.set('program_id', programId);
    }
    return this.http.get<TransactionRead[]>(`${this.base}/transactions`, {
      params,
    });
  }
}
