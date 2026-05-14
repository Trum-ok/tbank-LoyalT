import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  ApplicationCreate,
  ApplicationRead,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { PARTNER_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class ApplicationsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(PARTNER_API_BASE);

  submit(body: ApplicationCreate): Observable<ApplicationRead> {
    return this.http.post<ApplicationRead>(`${this.base}/applications`, body);
  }

  listMine(): Observable<ApplicationRead[]> {
    return this.http.get<ApplicationRead[]>(`${this.base}/applications/me`);
  }
}
