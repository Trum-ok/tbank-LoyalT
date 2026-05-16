import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AudiencePreview,
  BroadcastCreate,
  BroadcastRead,
  BroadcastSegment,
  BroadcastUpdate,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { PARTNER_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class BroadcastsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(PARTNER_API_BASE);

  list(): Observable<BroadcastRead[]> {
    return this.http.get<BroadcastRead[]>(`${this.base}/broadcasts`);
  }

  create(body: BroadcastCreate): Observable<BroadcastRead> {
    return this.http.post<BroadcastRead>(`${this.base}/broadcasts`, body);
  }

  update(id: string, body: BroadcastUpdate): Observable<BroadcastRead> {
    return this.http.patch<BroadcastRead>(
      `${this.base}/broadcasts/${id}`,
      body,
    );
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/broadcasts/${id}`);
  }

  send(id: string): Observable<BroadcastRead> {
    return this.http.post<BroadcastRead>(
      `${this.base}/broadcasts/${id}/send`,
      {},
    );
  }

  audience(
    segment: BroadcastSegment,
    programId?: string | null,
  ): Observable<AudiencePreview> {
    let params = new HttpParams().set('segment', segment);
    if (programId) params = params.set('program_id', programId);
    return this.http.get<AudiencePreview>(`${this.base}/broadcasts/audience`, {
      params,
    });
  }
}
