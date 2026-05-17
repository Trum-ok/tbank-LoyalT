import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { CustomerProfileRead, CustomerProfileUpdate } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { CORE_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class ProfileApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(CORE_API_BASE);

  get(): Observable<CustomerProfileRead> {
    return this.http.get<CustomerProfileRead>(`${this.base}/enrollments/me/profile`);
  }

  update(body: CustomerProfileUpdate): Observable<CustomerProfileRead> {
    return this.http.put<CustomerProfileRead>(
      `${this.base}/enrollments/me/profile`,
      body,
    );
  }
}
