import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AccountCreate,
  AccountRead,
  AccountUpdate,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { PARTNER_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class AccountsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(PARTNER_API_BASE);

  signup(body: AccountCreate): Observable<AccountRead> {
    return this.http.post<AccountRead>(`${this.base}/accounts`, body);
  }

  me(): Observable<AccountRead> {
    return this.http.get<AccountRead>(`${this.base}/accounts/me`);
  }

  updateMe(body: AccountUpdate): Observable<AccountRead> {
    return this.http.patch<AccountRead>(`${this.base}/accounts/me`, body);
  }
}
