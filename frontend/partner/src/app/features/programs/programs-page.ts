import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  ProgramCreate,
  ProgramRead,
  ProgramStatus,
  ProgramType,
} from '@tbank-loyalt/shared';
import { catchError, finalize, of } from 'rxjs';

import { ProgramsApi } from '../../core/api/programs-api.service';
import {
  formatDate,
  programStatusLabel,
  programTypeLabel,
} from '../../core/format';
import { NotifyService } from '../../core/notify.service';

type FilterStatus = ProgramStatus | 'all';

interface DraftForm {
  name: string;
  description: string;
  type: ProgramType;
  percent: number;
  points_per_visit: number;
  visits_required: number;
  points_ttl_days: number | null;
  expire_warn_days: number | null;
  min_redemption: number;
}

const TYPE_OPTIONS: { code: ProgramType; label: string; hint: string }[] = [
  {
    code: 'accrual',
    label: 'Накопительная',
    hint: 'Процент с чека идёт баллами',
  },
  {
    code: 'visit',
    label: 'За визит',
    hint: 'Фиксированные баллы за каждый визит',
  },
  {
    code: 'stamps',
    label: 'Штампы',
    hint: 'Каждый N-й визит — награда',
  },
];

@Component({
  selector: 'app-programs-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './programs-page.html',
  styleUrl: './programs-page.scss',
})
export class ProgramsPage {
  private readonly api = inject(ProgramsApi);
  private readonly router = inject(Router);
  private readonly notify = inject(NotifyService);

  readonly typeOptions = TYPE_OPTIONS;
  readonly programTypeLabel = programTypeLabel;
  readonly programStatusLabel = programStatusLabel;
  readonly formatDate = formatDate;

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly programs = signal<ProgramRead[]>([]);
  readonly filter = signal<FilterStatus>('all');

  readonly creatorOpen = signal(false);
  readonly creating = signal(false);
  readonly draft = signal<DraftForm>(this.defaultDraft());

  readonly counts = computed(() => {
    const all = this.programs();
    return {
      all: all.length,
      draft: all.filter(p => p.status === 'draft').length,
      published: all.filter(p => p.status === 'published').length,
      paused: all.filter(p => p.status === 'paused').length,
      archived: all.filter(p => p.status === 'archived').length,
    };
  });

  readonly filtered = computed(() => {
    const f = this.filter();
    return f === 'all'
      ? this.programs()
      : this.programs().filter(p => p.status === f);
  });

  constructor() {
    this.reload();
  }

  setFilter(value: FilterStatus): void {
    this.filter.set(value);
  }

  openCreator(): void {
    this.draft.set(this.defaultDraft());
    this.creatorOpen.set(true);
  }

  closeCreator(): void {
    this.creatorOpen.set(false);
  }

  patchDraft<K extends keyof DraftForm>(key: K, value: DraftForm[K]): void {
    this.draft.update(d => ({ ...d, [key]: value }));
  }

  create(): void {
    const d = this.draft();
    if (!d.name.trim()) {
      this.error.set('Название программы обязательно');
      return;
    }

    const accrual_rule = this.buildRule(d);
    const body: ProgramCreate = {
      name: d.name.trim(),
      description: d.description.trim() || null,
      type: d.type,
      accrual_rule,
      points_ttl_days: d.points_ttl_days,
      expire_warn_days: d.points_ttl_days ? d.expire_warn_days : null,
      min_redemption: d.min_redemption,
    };

    this.creating.set(true);
    this.error.set(null);
    this.api
      .create(body)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось создать программу';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.creating.set(false)),
      )
      .subscribe(p => {
        if (p) {
          this.closeCreator();
          this.notify.success(`Программа «${p.name}» создана`);
          this.router.navigate(['/programs', p.id]);
        }
      });
  }

  ruleSummary(p: ProgramRead): string {
    const rule = p.accrual_rule as Record<string, number>;
    switch (p.type) {
      case 'accrual':
        if (rule['percent'] !== undefined) return `${rule['percent']}% с чека`;
        if (rule['points_per_rub'] !== undefined)
          return `${rule['points_per_rub']} ₽ → 1 балл`;
        return 'накопительная';
      case 'visit':
        return `${rule['points_per_visit'] ?? '?'} баллов / визит`;
      case 'stamps':
        return `${rule['visits_required'] ?? '?'} визитов → награда`;
    }
  }

  private reload(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .list()
      .pipe(
        catchError(err => {
          this.error.set(
            err?.error?.detail ?? 'Не удалось загрузить программы',
          );
          return of([] as ProgramRead[]);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(rows => this.programs.set(rows));
  }

  private defaultDraft(): DraftForm {
    return {
      name: '',
      description: '',
      type: 'accrual',
      percent: 5,
      points_per_visit: 50,
      visits_required: 8,
      points_ttl_days: 365,
      expire_warn_days: 7,
      min_redemption: 100,
    };
  }

  private buildRule(d: DraftForm): Record<string, number> {
    switch (d.type) {
      case 'accrual':
        return { percent: d.percent };
      case 'visit':
        return { points_per_visit: d.points_per_visit };
      case 'stamps':
        return { visits_required: d.visits_required };
    }
  }
}
