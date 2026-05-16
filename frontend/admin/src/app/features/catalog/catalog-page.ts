import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  AdminBannerRead,
  AdminCategoryRead,
  AdminFeaturedPartnerRead,
  PartnerRead,
} from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { CatalogApi } from '../../core/api/catalog-api.service';
import { ModerationApi } from '../../core/api/moderation-api.service';
import { formatDate } from '../../core/format';
import { NotifyService } from '../../core/notify.service';

type Tab = 'categories' | 'featured' | 'banners';

interface CategoryDraft {
  label: string;
  description: string;
  display_order: number;
  is_active: boolean;
}

interface BannerDraft {
  title: string;
  body: string;
  image_url: string;
  link_url: string;
  position: number;
  is_active: boolean;
}

@Component({
  selector: 'app-catalog-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './catalog-page.html',
  styleUrl: './catalog-page.scss',
})
export class CatalogPage {
  private readonly api = inject(CatalogApi);
  private readonly moderationApi = inject(ModerationApi);
  private readonly notify = inject(NotifyService);

  readonly formatDate = formatDate;

  readonly tabs: { value: Tab; label: string }[] = [
    { value: 'categories', label: 'Категории' },
    { value: 'featured', label: 'Рекомендованные' },
    { value: 'banners', label: 'Баннеры' },
  ];

  readonly tab = signal<Tab>('categories');
  readonly loading = signal(true);
  readonly saving = signal(false);

  readonly categories = signal<AdminCategoryRead[]>([]);
  readonly featured = signal<AdminFeaturedPartnerRead[]>([]);
  readonly banners = signal<AdminBannerRead[]>([]);
  readonly partners = signal<PartnerRead[]>([]);

  // редактируемая категория
  readonly editCode = signal<string | null>(null);
  readonly catDraft = signal<CategoryDraft>(this.emptyCat());

  // новая запись featured
  readonly newFeaturedPartner = signal('');
  readonly newFeaturedPos = signal(0);

  // новый баннер
  readonly bannerDraft = signal<BannerDraft>(this.emptyBanner());

  constructor() {
    this.reload();
  }

  setTab(t: Tab): void {
    this.tab.set(t);
  }

  partnerName(id: string): string {
    return this.partners().find(p => p.id === id)?.name ?? id.slice(0, 8);
  }

  // ---------- категории ----------

  startEditCategory(c: AdminCategoryRead): void {
    this.editCode.set(c.code);
    this.catDraft.set({
      label: c.label,
      description: c.description ?? '',
      display_order: c.display_order,
      is_active: c.is_active,
    });
  }

  cancelEditCategory(): void {
    this.editCode.set(null);
  }

  saveCategory(code: string): void {
    const d = this.catDraft();
    if (!d.label.trim()) {
      this.notify.error('Название категории не может быть пустым');
      return;
    }
    this.saving.set(true);
    this.api
      .upsertCategory(code, {
        label: d.label.trim(),
        description: d.description.trim() || null,
        display_order: d.display_order,
        is_active: d.is_active,
      })
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось сохранить категорию');
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(updated => {
        if (updated) {
          this.notify.success('Категория сохранена');
          this.editCode.set(null);
          this.categories.update(list =>
            list.map(c => (c.code === updated.code ? updated : c)),
          );
        }
      });
  }

  // ---------- featured ----------

  addFeatured(): void {
    const partnerId = this.newFeaturedPartner();
    if (!partnerId) {
      this.notify.error('Выберите партнёра');
      return;
    }
    this.saving.set(true);
    this.api
      .addFeatured({ partner_id: partnerId, position: this.newFeaturedPos() })
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось добавить в рекомендованные');
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(res => {
        if (res) {
          this.notify.success('Партнёр добавлен в рекомендованные');
          this.featured.update(list => [...list, res]);
          this.newFeaturedPartner.set('');
          this.newFeaturedPos.set(0);
        }
      });
  }

  removeFeatured(id: string): void {
    this.api
      .removeFeatured(id)
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось удалить');
          return of(null);
        }),
      )
      .subscribe(() => {
        this.notify.success('Удалено из рекомендованных');
        this.featured.update(list => list.filter(f => f.id !== id));
      });
  }

  // ---------- баннеры ----------

  createBanner(): void {
    const d = this.bannerDraft();
    if (!d.title.trim()) {
      this.notify.error('Заголовок баннера обязателен');
      return;
    }
    this.saving.set(true);
    this.api
      .createBanner({
        title: d.title.trim(),
        body: d.body.trim() || null,
        image_url: d.image_url.trim() || null,
        link_url: d.link_url.trim() || null,
        position: d.position,
        is_active: d.is_active,
      })
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось создать баннер');
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(res => {
        if (res) {
          this.notify.success('Баннер создан');
          this.banners.update(list => [...list, res]);
          this.bannerDraft.set(this.emptyBanner());
        }
      });
  }

  toggleBanner(b: AdminBannerRead): void {
    this.api
      .updateBanner(b.id, { is_active: !b.is_active })
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось изменить баннер');
          return of(null);
        }),
      )
      .subscribe(updated => {
        if (updated) {
          this.banners.update(list =>
            list.map(x => (x.id === updated.id ? updated : x)),
          );
        }
      });
  }

  deleteBanner(id: string): void {
    this.api
      .deleteBanner(id)
      .pipe(
        catchError(() => {
          this.notify.error('Не удалось удалить баннер');
          return of(null);
        }),
      )
      .subscribe(() => {
        this.notify.success('Баннер удалён');
        this.banners.update(list => list.filter(b => b.id !== id));
      });
  }

  // ---------- patch draft helpers ----------

  patchCat<K extends keyof CategoryDraft>(
    key: K,
    value: CategoryDraft[K],
  ): void {
    this.catDraft.update(d => ({ ...d, [key]: value }));
  }

  patchBanner<K extends keyof BannerDraft>(
    key: K,
    value: BannerDraft[K],
  ): void {
    this.bannerDraft.update(d => ({ ...d, [key]: value }));
  }

  private reload(): void {
    this.loading.set(true);
    this.api
      .listCategories()
      .pipe(catchError(() => of([] as AdminCategoryRead[])))
      .subscribe(c => this.categories.set(c));
    this.api
      .listFeatured()
      .pipe(catchError(() => of([] as AdminFeaturedPartnerRead[])))
      .subscribe(f => this.featured.set(f));
    this.moderationApi
      .listPartners({ limit: 200 })
      .pipe(catchError(() => of([] as PartnerRead[])))
      .subscribe(p => this.partners.set(p));
    this.api
      .listBanners(false)
      .pipe(
        catchError(() => of([] as AdminBannerRead[])),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(b => this.banners.set(b));
  }

  private emptyCat(): CategoryDraft {
    return { label: '', description: '', display_order: 0, is_active: true };
  }

  private emptyBanner(): BannerDraft {
    return {
      title: '',
      body: '',
      image_url: '',
      link_url: '',
      position: 0,
      is_active: true,
    };
  }
}
