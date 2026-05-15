import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { StaffCreate, StaffRead, StaffUpdate } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { PARTNER_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class StaffApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(PARTNER_API_BASE);

  list(): Observable<StaffRead[]> {
    return this.http.get<StaffRead[]>(`${this.base}/staff`);
  }

  create(body: StaffCreate): Observable<StaffRead> {
    return this.http.post<StaffRead>(`${this.base}/staff`, body);
  }

  update(staffId: string, body: StaffUpdate): Observable<StaffRead> {
    return this.http.patch<StaffRead>(`${this.base}/staff/${staffId}`, body);
  }

  remove(staffId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/staff/${staffId}`);
  }
}
