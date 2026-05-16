import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AdminDecisionRequest,
  ApplicationRead,
  PartnerRead,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { ADMIN_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class ModerationApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(ADMIN_API_BASE);

  // --- заявки ---

  listApplications(opts: {
    status?: string | null;
    limit?: number;
    offset?: number;
  } = {}): Observable<ApplicationRead[]> {
    let params = new HttpParams();
    if (opts.status) params = params.set('status', opts.status);
    params = params.set('limit', String(opts.limit ?? 50));
    params = params.set('offset', String(opts.offset ?? 0));
    return this.http.get<ApplicationRead[]>(
      `${this.base}/moderation/applications`,
      { params },
    );
  }

  getApplication(id: string): Observable<ApplicationRead> {
    return this.http.get<ApplicationRead>(
      `${this.base}/moderation/applications/${id}`,
    );
  }

  /** Одобрение заявки — создаёт партнёра, возвращает его профиль. */
  approve(id: string, body: AdminDecisionRequest): Observable<PartnerRead> {
    return this.http.post<PartnerRead>(
      `${this.base}/moderation/applications/${id}/approve`,
      body,
    );
  }

  reject(id: string, body: AdminDecisionRequest): Observable<ApplicationRead> {
    return this.http.post<ApplicationRead>(
      `${this.base}/moderation/applications/${id}/reject`,
      body,
    );
  }

  // --- партнёры ---

  listPartners(opts: {
    status?: string | null;
    limit?: number;
    offset?: number;
  } = {}): Observable<PartnerRead[]> {
    let params = new HttpParams();
    if (opts.status) params = params.set('status', opts.status);
    params = params.set('limit', String(opts.limit ?? 50));
    params = params.set('offset', String(opts.offset ?? 0));
    return this.http.get<PartnerRead[]>(`${this.base}/moderation/partners`, {
      params,
    });
  }

  getPartner(id: string): Observable<PartnerRead> {
    return this.http.get<PartnerRead>(
      `${this.base}/moderation/partners/${id}`,
    );
  }

  suspendPartner(id: string): Observable<PartnerRead> {
    return this.http.post<PartnerRead>(
      `${this.base}/moderation/partners/${id}/suspend`,
      {},
    );
  }

  blockPartner(id: string): Observable<PartnerRead> {
    return this.http.post<PartnerRead>(
      `${this.base}/moderation/partners/${id}/block`,
      {},
    );
  }

  unblockPartner(id: string): Observable<PartnerRead> {
    return this.http.post<PartnerRead>(
      `${this.base}/moderation/partners/${id}/unblock`,
      {},
    );
  }
}
