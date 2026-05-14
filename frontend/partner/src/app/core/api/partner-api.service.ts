import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { PartnerRead, PartnerUpdate } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { PARTNER_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class PartnerApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(PARTNER_API_BASE);

  me(): Observable<PartnerRead> {
    return this.http.get<PartnerRead>(`${this.base}/partners/me`);
  }

  updateMe(body: PartnerUpdate): Observable<PartnerRead> {
    return this.http.patch<PartnerRead>(`${this.base}/partners/me`, body);
  }
}
