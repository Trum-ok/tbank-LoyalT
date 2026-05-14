import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  RewardCreate,
  RewardRead,
  RewardUpdate,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class RewardsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  list(programId: string, onlyActive = false): Observable<RewardRead[]> {
    const params = new HttpParams().set('only_active', String(onlyActive));
    return this.http.get<RewardRead[]>(
      `${this.base}/programs/${programId}/rewards`,
      { params },
    );
  }

  create(programId: string, body: RewardCreate): Observable<RewardRead> {
    return this.http.post<RewardRead>(
      `${this.base}/programs/${programId}/rewards`,
      body,
    );
  }

  update(rewardId: string, body: RewardUpdate): Observable<RewardRead> {
    return this.http.patch<RewardRead>(
      `${this.base}/rewards/${rewardId}`,
      body,
    );
  }

  delete(rewardId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/rewards/${rewardId}`);
  }
}
