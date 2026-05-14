import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  CatalogCategory,
  CatalogProgram,
  CatalogProgramDetail,
  PartnerCategory,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

export interface CatalogSearchParams {
  category?: PartnerCategory | null;
  q?: string | null;
  limit?: number;
  offset?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  search(params: CatalogSearchParams = {}): Observable<CatalogProgram[]> {
    let httpParams = new HttpParams();
    if (params.category) {
      httpParams = httpParams.set('category', params.category);
    }
    if (params.q) {
      httpParams = httpParams.set('q', params.q);
    }
    if (params.limit !== undefined) {
      httpParams = httpParams.set('limit', String(params.limit));
    }
    if (params.offset !== undefined) {
      httpParams = httpParams.set('offset', String(params.offset));
    }
    return this.http.get<CatalogProgram[]>(`${this.base}/catalog/programs`, {
      params: httpParams,
    });
  }

  getProgram(programId: string): Observable<CatalogProgramDetail> {
    return this.http.get<CatalogProgramDetail>(
      `${this.base}/catalog/programs/${programId}`,
    );
  }

  listCategories(): Observable<CatalogCategory[]> {
    return this.http.get<CatalogCategory[]>(`${this.base}/catalog/categories`);
  }
}
