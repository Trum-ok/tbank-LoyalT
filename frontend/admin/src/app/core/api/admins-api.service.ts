import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { AdminCreate, AdminRead, AdminUpdate } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { ADMIN_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class AdminsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(ADMIN_API_BASE);

  /** Создание администратора. Без X-Admin-Id работает только при bootstrap
   *  (пустая таблица), иначе требует активного админа в заголовке. */
  create(body: AdminCreate): Observable<AdminRead> {
    return this.http.post<AdminRead>(`${this.base}/admins`, body);
  }

  list(): Observable<AdminRead[]> {
    return this.http.get<AdminRead[]>(`${this.base}/admins`);
  }

  me(): Observable<AdminRead> {
    return this.http.get<AdminRead>(`${this.base}/admins/me`);
  }

  update(id: string, body: AdminUpdate): Observable<AdminRead> {
    return this.http.patch<AdminRead>(`${this.base}/admins/${id}`, body);
  }
}
