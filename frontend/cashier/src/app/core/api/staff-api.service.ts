import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  StaffLoginRequest,
  StaffLoginResponse,
  StaffRead,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { PARTNER_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class StaffApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(PARTNER_API_BASE);

  login(body: StaffLoginRequest): Observable<StaffLoginResponse> {
    return this.http.post<StaffLoginResponse>(
      `${this.base}/staff/login`,
      body,
    );
  }

  me(): Observable<StaffRead> {
    return this.http.get<StaffRead>(`${this.base}/staff/me`);
  }
}
