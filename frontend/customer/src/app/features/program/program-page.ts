import { Component, DestroyRef, computed, effect, inject, input, signal } from '@angular/core';
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
import { NotifyService } from '../../core/notify.service';
import { PageActionsService } from '../../core/page-actions.service';

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
  private readonly notify = inject(NotifyService);
  private readonly pageActions = inject(PageActionsService);
  private readonly destroyRef = inject(DestroyRef);

  readonly id = input.required<string>();
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly program = signal<CatalogProgramDetail | null>(null);
  readonly myEnrollments = signal<EnrollmentRead[]>([]);
  readonly enrolling = signal(false);
  readonly mutating = signal(false);
  readonly qrOpen = signal(false);

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

  readonly displayName = computed(() => {
    const e = this.existingEnrollment();
    const p = this.program();
    return e?.display_name?.trim() || p?.program_name || '';
  });

  readonly qrUrl = computed(() => {
    const e = this.existingEnrollment();
    if (!e) return null;
    const payload = `tbank-loyalt:enrollment:${e.id}`;
    return `https://api.qrserver.com/v1/create-qr-code/?size=320x320&margin=12&data=${encodeURIComponent(payload)}`;
  });

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

    effect(() => {
      const e = this.existingEnrollment();
      if (!e) {
        this.pageActions.set([]);
        return;
      }
      this.pageActions.set([
        {
          id: 'archive',
          icon: e.is_archived ? 'unarchive' : 'archive',
          label: e.is_archived ? 'Разархивировать' : 'В архив',
          disabled: this.mutating(),
          handler: () => this.toggleArchive(),
        },
        {
          id: 'remove',
          icon: 'trash',
          label: 'Удалить',
          danger: true,
          disabled: this.mutating(),
          handler: () => this.remove(),
        },
      ]);
    });

    this.destroyRef.onDestroy(() => this.pageActions.clear());
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

  openQr(): void {
    if (!this.existingEnrollment() || this.isArchived()) return;
    this.qrOpen.set(true);
  }

  closeQr(): void {
    this.qrOpen.set(false);
  }

  rename(): void {
    const e = this.existingEnrollment();
    const p = this.program();
    if (!e || !p) return;
    const current = e.display_name ?? p.program_name;
    const next = prompt('Как назвать программу у себя?', current);
    if (next === null) return;
    const trimmed = next.trim();
    if (trimmed === (e.display_name ?? '').trim()) return;
    this.mutating.set(true);
    this.error.set(null);
    this.enrollmentsApi
      .update(e.id, { display_name: trimmed || null })
      .pipe(finalize(() => this.mutating.set(false)))
      .subscribe({
        next: () => {
          this.store.refresh();
          this.refresh(this.id());
          this.notify.success('Название обновлено');
        },
        error: err => {
          const msg = err?.error?.detail ?? 'Не удалось переименовать';
          this.error.set(msg);
          this.notify.error(msg);
        },
      });
  }

  toggleArchive(): void {
    const e = this.existingEnrollment();
    if (!e) return;
    const willArchive = !e.is_archived;
    const message = willArchive
      ? 'Перенести программу в архив? Она пропадёт из основного списка.'
      : 'Вернуть программу из архива?';
    if (!confirm(message)) return;
    this.mutating.set(true);
    this.error.set(null);
    this.enrollmentsApi
      .update(e.id, { is_archived: willArchive })
      .pipe(finalize(() => this.mutating.set(false)))
      .subscribe({
        next: () => {
          this.store.refresh();
          this.refresh(this.id());
          this.notify.success(
            willArchive ? 'Программа в архиве' : 'Программа возвращена',
          );
        },
        error: err => {
          const msg = err?.error?.detail ?? 'Не удалось изменить статус';
          this.error.set(msg);
          this.notify.error(msg);
        },
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
          this.notify.success('Программа удалена');
        },
        error: err => {
          const msg = err?.error?.detail ?? 'Не удалось удалить';
          this.error.set(msg);
          this.notify.error(msg);
        },
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
