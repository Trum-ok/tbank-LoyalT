import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { Router } from '@angular/router';
import { TuiLoader } from '@taiga-ui/core';
import { TuiAvatar } from '@taiga-ui/kit';
import {
  CatalogProgramDetail,
  EnrollmentRead,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { CatalogApi } from '../../core/api/catalog-api.service';
import { EnrollmentsApi } from '../../core/api/enrollments-api.service';
import { EnrollmentsStore } from '../../core/enrollments.store';
import { formatPoints } from '../../core/format';

interface Highlight {
  value: string;
  unit: string;
}

@Component({
  selector: 'app-program-page',
  standalone: true,
  imports: [TuiAvatar, TuiLoader],
  templateUrl: './program-page.html',
  styleUrl: './program-page.scss',
})
export class ProgramPage {
  private readonly catalog = inject(CatalogApi);
  private readonly enrollmentsApi = inject(EnrollmentsApi);
  private readonly store = inject(EnrollmentsStore);
  private readonly router = inject(Router);

  readonly id = input.required<string>();
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly program = signal<CatalogProgramDetail | null>(null);
  readonly myEnrollments = signal<EnrollmentRead[]>([]);
  readonly enrolling = signal(false);
  readonly mutating = signal(false);

  readonly existingEnrollment = computed(() => {
    const p = this.program();
    if (!p) {
      return null;
    }
    return (
      this.myEnrollments().find(e => e.program_id === p.program_id) ?? null
    );
  });

  readonly isArchived = computed(
    () => this.existingEnrollment()?.is_archived ?? false,
  );

  readonly formatPoints = formatPoints;

  readonly highlight = computed<Highlight | null>(() => {
    const p = this.program();
    if (!p) return null;
    const r = p.accrual_rule;
    switch (p.type) {
      case 'accrual':
        if (typeof r['percent'] === 'number') {
          return { value: `${r['percent']}%`, unit: 'от покупки' };
        }
        if (typeof r['points_per_rub'] === 'number') {
          return { value: `×${r['points_per_rub']}`, unit: 'балл на ₽' };
        }
        return null;
      case 'visit':
        return { value: `+${r['points_per_visit'] ?? '?'}`, unit: 'балла за визит' };
      case 'stamps':
        return { value: `${r['visits_required'] ?? '?'}`, unit: 'визитов до награды' };
      default:
        return null;
    }
  });

  readonly typeLabel = computed(() => {
    const p = this.program();
    if (!p) return '';
    switch (p.type) {
      case 'accrual':
        return 'Кешбэк баллами';
      case 'visit':
        return 'Баллы за визит';
      case 'stamps':
        return 'Штампы';
    }
  });

  constructor() {
    effect(() => {
      const id = this.id();
      this.refresh(id);
    });
  }

  initials(name: string): string {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(s => s[0]?.toUpperCase() ?? '')
      .join('');
  }

  enroll(): void {
    const p = this.program();
    if (!p) return;
    this.enrolling.set(true);
    this.enrollmentsApi
      .create({ program_id: p.program_id })
      .pipe(finalize(() => this.enrolling.set(false)))
      .subscribe({
        next: () => {
          this.store.refresh();
          this.router.navigateByUrl('/my-programs');
        },
        error: err => this.error.set(err?.error?.detail ?? 'Не удалось подключиться'),
      });
  }

  toggleArchive(): void {
    const e = this.existingEnrollment();
    if (!e) return;
    this.mutating.set(true);
    this.error.set(null);
    this.enrollmentsApi
      .update(e.id, { is_archived: !e.is_archived })
      .pipe(finalize(() => this.mutating.set(false)))
      .subscribe({
        next: () => {
          this.store.refresh();
          this.refresh(this.id());
        },
        error: err =>
          this.error.set(err?.error?.detail ?? 'Не удалось изменить статус'),
      });
  }

  remove(): void {
    const e = this.existingEnrollment();
    if (!e) return;
    if (!confirm('Удалить программу из подключённых?')) return;
    this.mutating.set(true);
    this.error.set(null);
    this.enrollmentsApi
      .remove(e.id)
      .pipe(finalize(() => this.mutating.set(false)))
      .subscribe({
        next: () => {
          this.store.refresh();
          this.router.navigateByUrl('/my-programs');
        },
        error: err =>
          this.error.set(err?.error?.detail ?? 'Не удалось удалить'),
      });
  }

  private refresh(id: string): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      program: this.catalog.getProgram(id).pipe(
        catchError(err => {
          this.error.set(
            err?.status === 404
              ? 'Программа не найдена'
              : err?.message ?? 'Ошибка',
          );
          return of(null);
        }),
      ),
      enrollments: this.enrollmentsApi
        .list(true)
        .pipe(catchError(() => of([] as EnrollmentRead[]))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ program, enrollments }) => {
        this.program.set(program);
        this.myEnrollments.set(enrollments);
      });
  }
}
