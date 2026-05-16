import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  BroadcastCreate,
  BroadcastRead,
  BroadcastSegment,
  BroadcastUpdate,
  ProgramRead,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { BroadcastsApi } from '../../core/api/broadcasts-api.service';
import { ProgramsApi } from '../../core/api/programs-api.service';
import { formatDateTime } from '../../core/format';
import { NotifyService } from '../../core/notify.service';

interface SegmentOption {
  code: BroadcastSegment;
  label: string;
  hint: string;
}

const SEGMENTS: SegmentOption[] = [
  {
    code: 'all_enrolled',
    label: 'Все подключённые',
    hint: 'Все клиенты с активным участием в программах',
  },
  {
    code: 'active_30d',
    label: 'Активные (30 дней)',
    hint: 'Была операция за последние 30 дней',
  },
  {
    code: 'by_program',
    label: 'По программе',
    hint: 'Клиенты выбранной программы',
  },
  {
    code: 'balance_positive',
    label: 'С балансом > 0',
    hint: 'Есть накопленные баллы — напомнить потратить',
  },
  {
    code: 'new_7d',
    label: 'Новые (7 дней)',
    hint: 'Вступили за последнюю неделю',
  },
];

@Component({
  selector: 'app-broadcasts-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './broadcasts-page.html',
  styleUrl: './broadcasts-page.scss',
})
export class BroadcastsPage {
  private readonly api = inject(BroadcastsApi);
  private readonly programsApi = inject(ProgramsApi);
  private readonly notify = inject(NotifyService);

  readonly segments = SEGMENTS;
  readonly formatDateTime = formatDateTime;

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly broadcasts = signal<BroadcastRead[]>([]);
  readonly programs = signal<ProgramRead[]>([]);

  readonly editingId = signal<string | null>(null);
  readonly title = signal('');
  readonly body = signal('');
  readonly segment = signal<BroadcastSegment>('all_enrolled');
  readonly programId = signal<string | null>(null);

  readonly audienceCount = signal<number | null>(null);
  readonly audienceLoading = signal(false);
  readonly saving = signal(false);
  readonly sending = signal(false);

  readonly drafts = computed(() =>
    this.broadcasts().filter(b => b.status === 'draft'),
  );
  readonly history = computed(() =>
    this.broadcasts().filter(b => b.status !== 'draft'),
  );

  readonly segmentHint = computed(
    () => this.segments.find(s => s.code === this.segment())?.hint ?? '',
  );
  readonly needsProgram = computed(() => this.segment() === 'by_program');
  readonly canSubmit = computed(
    () =>
      this.title().trim().length > 0 &&
      this.body().trim().length > 0 &&
      (!this.needsProgram() || !!this.programId()),
  );

  constructor() {
    this.reload();
  }

  segmentLabel(code: BroadcastSegment): string {
    return this.segments.find(s => s.code === code)?.label ?? code;
  }

  programName(id: string | null): string {
    if (!id) return '—';
    return this.programs().find(p => p.id === id)?.name ?? id.slice(0, 8);
  }

  onSegmentChange(value: BroadcastSegment): void {
    this.segment.set(value);
    if (value !== 'by_program') this.programId.set(null);
    this.refreshAudience();
  }

  onProgramChange(value: string): void {
    this.programId.set(value || null);
    this.refreshAudience();
  }

  refreshAudience(): void {
    if (this.needsProgram() && !this.programId()) {
      this.audienceCount.set(null);
      return;
    }
    this.audienceLoading.set(true);
    this.api
      .audience(this.segment(), this.programId())
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.audienceLoading.set(false)),
      )
      .subscribe(res => this.audienceCount.set(res?.count ?? null));
  }

  newDraft(): void {
    this.editingId.set(null);
    this.title.set('');
    this.body.set('');
    this.segment.set('all_enrolled');
    this.programId.set(null);
    this.error.set(null);
    this.refreshAudience();
  }

  editDraft(b: BroadcastRead): void {
    this.editingId.set(b.id);
    this.title.set(b.title);
    this.body.set(b.body);
    this.segment.set(b.segment);
    this.programId.set(b.program_id);
    this.error.set(null);
    this.refreshAudience();
  }

  saveDraft(): void {
    if (!this.canSubmit() || this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    this.persist()
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe(saved => {
        if (saved) {
          this.editingId.set(saved.id);
          this.notify.success('Черновик сохранён');
          this.reload();
        }
      });
  }

  sendCurrent(): void {
    if (!this.canSubmit() || this.sending()) return;
    this.sending.set(true);
    this.error.set(null);
    // Сначала сохраняем (создаём/обновляем), затем отправляем по id.
    this.persist().subscribe(saved => {
      if (!saved) {
        this.sending.set(false);
        return;
      }
      this.api
        .send(saved.id)
        .pipe(
          catchError(err => {
            const msg = err?.error?.detail ?? 'Не удалось отправить рассылку';
            this.error.set(msg);
            this.notify.error(msg);
            return of(null);
          }),
          finalize(() => this.sending.set(false)),
        )
        .subscribe(res => {
          if (res) {
            this.notify.success(
              `Рассылка отправлена · ${res.sent_count ?? 0} получателей`,
            );
            this.newDraft();
            this.reload();
          }
        });
    });
  }

  deleteDraft(b: BroadcastRead): void {
    this.api
      .remove(b.id)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось удалить черновик';
          this.notify.error(msg);
          return of(null);
        }),
      )
      .subscribe(() => {
        if (this.editingId() === b.id) this.newDraft();
        this.notify.success('Черновик удалён');
        this.reload();
      });
  }

  private persist() {
    const editingId = this.editingId();
    if (editingId) {
      const body: BroadcastUpdate = {
        title: this.title().trim(),
        body: this.body().trim(),
        segment: this.segment(),
        program_id: this.needsProgram() ? this.programId() : null,
      };
      return this.api.update(editingId, body).pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось сохранить черновик';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
      );
    }
    const body: BroadcastCreate = {
      title: this.title().trim(),
      body: this.body().trim(),
      segment: this.segment(),
      program_id: this.needsProgram() ? this.programId() : null,
    };
    return this.api.create(body).pipe(
      catchError(err => {
        const msg = err?.error?.detail ?? 'Не удалось создать черновик';
        this.error.set(msg);
        this.notify.error(msg);
        return of(null);
      }),
    );
  }

  private reload(): void {
    this.loading.set(true);
    forkJoin({
      broadcasts: this.api.list().pipe(catchError(() => of([] as BroadcastRead[]))),
      programs: this.programsApi
        .list()
        .pipe(catchError(() => of([] as ProgramRead[]))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ broadcasts, programs }) => {
        this.broadcasts.set(broadcasts);
        this.programs.set(programs);
        if (this.audienceCount() === null) this.refreshAudience();
      });
  }
}
