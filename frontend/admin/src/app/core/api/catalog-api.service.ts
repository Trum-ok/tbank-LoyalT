import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AdminBannerCreate,
  AdminBannerRead,
  AdminBannerUpdate,
  AdminCategoryRead,
  AdminCategoryUpsert,
  AdminFeaturedPartnerCreate,
  AdminFeaturedPartnerRead,
} from '@tbank-loyalt/shared';
import { Observable } from 'rxjs';

import { ADMIN_API_BASE } from '../api-base.tokens';

@Injectable({ providedIn: 'root' })
export class CatalogApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(ADMIN_API_BASE);

  // --- категории ---

  listCategories(): Observable<AdminCategoryRead[]> {
    return this.http.get<AdminCategoryRead[]>(
      `${this.base}/catalog/categories`,
    );
  }

  upsertCategory(
    code: string,
    body: AdminCategoryUpsert,
  ): Observable<AdminCategoryRead> {
    return this.http.put<AdminCategoryRead>(
      `${this.base}/catalog/categories/${code}`,
      body,
    );
  }

  // --- рекомендованные партнёры ---

  listFeatured(): Observable<AdminFeaturedPartnerRead[]> {
    return this.http.get<AdminFeaturedPartnerRead[]>(
      `${this.base}/catalog/featured`,
    );
  }

  addFeatured(
    body: AdminFeaturedPartnerCreate,
  ): Observable<AdminFeaturedPartnerRead> {
    return this.http.post<AdminFeaturedPartnerRead>(
      `${this.base}/catalog/featured`,
      body,
    );
  }

  removeFeatured(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/catalog/featured/${id}`);
  }

  // --- баннеры ---

  listBanners(activeOnly = false): Observable<AdminBannerRead[]> {
    const params = new HttpParams().set('active_only', String(activeOnly));
    return this.http.get<AdminBannerRead[]>(`${this.base}/catalog/banners`, {
      params,
    });
  }

  createBanner(body: AdminBannerCreate): Observable<AdminBannerRead> {
    return this.http.post<AdminBannerRead>(
      `${this.base}/catalog/banners`,
      body,
    );
  }

  updateBanner(
    id: string,
    body: AdminBannerUpdate,
  ): Observable<AdminBannerRead> {
    return this.http.patch<AdminBannerRead>(
      `${this.base}/catalog/banners/${id}`,
      body,
    );
  }

  deleteBanner(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/catalog/banners/${id}`);
  }
}
