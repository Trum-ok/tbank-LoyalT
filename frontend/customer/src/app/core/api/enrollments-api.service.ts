import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { EnrollmentCreate, EnrollmentRead } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class EnrollmentsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  list(includeArchived = false): Observable<EnrollmentRead[]> {
    const params = new HttpParams().set(
      'include_archived',
      String(includeArchived),
    );
    return this.http.get<EnrollmentRead[]>(`${this.base}/enrollments`, {
      params,
    });
  }

  create(body: EnrollmentCreate): Observable<EnrollmentRead> {
    return this.http.post<EnrollmentRead>(`${this.base}/enrollments`, body);
  }
}
