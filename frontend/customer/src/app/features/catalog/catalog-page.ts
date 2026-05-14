import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TuiLoader } from '@taiga-ui/core';
import { TuiAvatar } from '@taiga-ui/kit';
import {
  CatalogCategory,
  CatalogProgram,
  PartnerCategory,
} from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { CatalogApi } from '../../core/api/catalog-api.service';

@Component({
  selector: 'app-catalog-page',
  standalone: true,
  imports: [RouterLink, TuiAvatar, TuiLoader],
  templateUrl: './catalog-page.html',
  styleUrl: './catalog-page.scss',
})
export class CatalogPage {
  private readonly api = inject(CatalogApi);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly programs = signal<CatalogProgram[]>([]);
  readonly categories = signal<CatalogCategory[]>([]);
  readonly activeCategory = signal<PartnerCategory | null>(null);
  readonly query = signal('');

  readonly hero = computed<CatalogProgram | null>(() => this.programs()[0] ?? null);
  readonly restPrograms = computed(() => this.programs().slice(1));

  constructor() {
    this.api
      .listCategories()
      .pipe(catchError(() => of([])))
      .subscribe(c => this.categories.set(c));
    this.reload();
  }

  selectCategory(category: PartnerCategory | null): void {
    this.activeCategory.set(category);
    this.reload();
  }

  applyQuery(value: string): void {
    this.query.set(value);
    this.reload();
  }

  initials(name: string): string {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(s => s[0]?.toUpperCase() ?? '')
      .join('');
  }

  typeShortLabel(t: CatalogProgram['type']): string {
    switch (t) {
      case 'accrual':
        return 'кешбэк';
      case 'visit':
        return 'визиты';
      case 'stamps':
        return 'штампы';
    }
  }

  private reload(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .search({ category: this.activeCategory(), q: this.query() })
      .pipe(
        catchError(err => {
          this.error.set(err?.message ?? 'Не удалось загрузить каталог');
          return of([] as CatalogProgram[]);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.programs.set(rows));
  }
}
