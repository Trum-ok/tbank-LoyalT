import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { NotificationRead } from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { NOTIFICATION_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class NotificationsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(NOTIFICATION_API_BASE);

  list(unreadOnly = false): Observable<NotificationRead[]> {
    const params = new HttpParams().set('unread_only', String(unreadOnly));
    return this.http.get<NotificationRead[]>(`${this.base}/notifications`, {
      params,
    });
  }

  markRead(id: string): Observable<NotificationRead> {
    return this.http.post<NotificationRead>(
      `${this.base}/notifications/${id}/read`,
      {},
    );
  }
}
