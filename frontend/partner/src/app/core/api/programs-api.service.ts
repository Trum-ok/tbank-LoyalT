import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  ProgramCreate,
  ProgramRead,
  ProgramUpdate,
  TierCreate,
  TierUpdate,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class ProgramsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  list(): Observable<ProgramRead[]> {
    return this.http.get<ProgramRead[]>(`${this.base}/programs`);
  }

  get(programId: string): Observable<ProgramRead> {
    return this.http.get<ProgramRead>(`${this.base}/programs/${programId}`);
  }

  create(body: ProgramCreate): Observable<ProgramRead> {
    return this.http.post<ProgramRead>(`${this.base}/programs`, body);
  }

  update(programId: string, body: ProgramUpdate): Observable<ProgramRead> {
    return this.http.patch<ProgramRead>(
      `${this.base}/programs/${programId}`,
      body,
    );
  }

  publish(programId: string): Observable<ProgramRead> {
    return this.http.post<ProgramRead>(
      `${this.base}/programs/${programId}/publish`,
      {},
    );
  }

  pause(programId: string): Observable<ProgramRead> {
    return this.http.post<ProgramRead>(
      `${this.base}/programs/${programId}/pause`,
      {},
    );
  }

  archive(programId: string): Observable<ProgramRead> {
    return this.http.post<ProgramRead>(
      `${this.base}/programs/${programId}/archive`,
      {},
    );
  }

  addTier(programId: string, body: TierCreate): Observable<ProgramRead> {
    return this.http.post<ProgramRead>(
      `${this.base}/programs/${programId}/tiers`,
      body,
    );
  }

  updateTier(
    programId: string,
    tierId: string,
    body: TierUpdate,
  ): Observable<ProgramRead> {
    return this.http.patch<ProgramRead>(
      `${this.base}/programs/${programId}/tiers/${tierId}`,
      body,
    );
  }

  deleteTier(programId: string, tierId: string): Observable<ProgramRead> {
    return this.http.delete<ProgramRead>(
      `${this.base}/programs/${programId}/tiers/${tierId}`,
    );
  }
}
