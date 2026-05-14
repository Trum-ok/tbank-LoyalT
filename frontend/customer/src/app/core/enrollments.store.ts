import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { EnrollmentRead } from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { EnrollmentsApi } from './api/enrollments-api.service';
import { CustomerIdService } from './customer-id.service';

@Injectable({ providedIn: 'root' })
export class EnrollmentsStore {
  private readonly api = inject(EnrollmentsApi);
  private readonly customer = inject(CustomerIdService);

  private readonly _items = signal<EnrollmentRead[]>([]);
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);

  readonly items = this._items.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();

  readonly totalBalance = computed(() =>
    this._items().reduce((sum, e) => sum + e.points_balance, 0),
  );

  readonly topByBalance = computed(() =>
    [...this._items()]
      .sort((a, b) => b.points_balance - a.points_balance)
      .slice(0, 4),
  );

  constructor() {
    effect(() => {
      this.customer.currentId();
      this.refresh();
    });
  }

  refresh(): void {
    this._loading.set(true);
    this._error.set(null);
    this.api
      .list(false)
      .pipe(
        catchError(err => {
          this._error.set(err?.message ?? 'Не удалось загрузить программы');
          return of([] as EnrollmentRead[]);
        }),
        finalize(() => this._loading.set(false)),
      )
      .subscribe(items => this._items.set(items));
  }
}
