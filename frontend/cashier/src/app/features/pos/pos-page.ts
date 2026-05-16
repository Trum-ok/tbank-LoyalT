import {
  Component,
  ElementRef,
  OnDestroy,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import {
  AccruePayload,
  EnrollmentLookup,
  RewardOption,
} from '@tbank-loyalt/shared';
import jsQR from 'jsqr';
import { catchError, finalize, Observable, of } from 'rxjs';

import { PointsApi } from '../../core/api/points-api.service';
import {
  formatPoints,
  formatPointsLabel,
  parseEnrollmentCode,
  parseShortCode,
  pointsWord,
  programTypeLabel,
} from '../../core/format';
import { NotifyService } from '../../core/notify.service';

type Stage = 'scan' | 'client' | 'done';

interface DoneInfo {
  kind: 'accrual' | 'redemption';
  points: number;
  balanceAfter: number;
  transactionId: string;
}

@Component({
  selector: 'app-pos-page',
  standalone: true,
  templateUrl: './pos-page.html',
  styleUrl: './pos-page.scss',
})
export class PosPage implements OnDestroy {
  private readonly pointsApi = inject(PointsApi);
  private readonly notify = inject(NotifyService);

  private readonly videoRef =
    viewChild<ElementRef<HTMLVideoElement>>('video');

  readonly formatPoints = formatPoints;
  readonly formatPointsLabel = formatPointsLabel;
  readonly pointsWord = pointsWord;
  readonly programTypeLabel = programTypeLabel;

  readonly stage = signal<Stage>('scan');
  readonly busy = signal(false);
  readonly cameraOn = signal(false);
  readonly cameraError = signal<string | null>(null);
  readonly manualCode = signal('');

  readonly client = signal<EnrollmentLookup | null>(null);
  readonly done = signal<DoneInfo | null>(null);
  readonly confirmUndo = signal(false);

  // Форма начисления
  readonly amount = signal('');
  readonly visits = signal(1);
  readonly manualPoints = signal('');
  readonly accrueError = signal<string | null>(null);

  private stream: MediaStream | null = null;
  private rafId: number | null = null;
  private scanCanvas = document.createElement('canvas');

  readonly accrualMode = computed<'amount' | 'visits'>(() => {
    const c = this.client();
    return c?.program_type === 'accrual' ? 'amount' : 'visits';
  });

  /**
   * Сколько баллов будет начислено — повторяет _calculate_points
   * из core-service. null = посчитать нельзя (нет ввода / правило кривое).
   */
  readonly previewPoints = computed<number | null>(() => {
    const c = this.client();
    if (!c) return null;

    const manual = Number(this.manualPoints());
    if (this.manualPoints().trim() && manual > 0) {
      return Math.floor(manual);
    }

    const rule = c.accrual_rule ?? {};
    const num = (key: string): number | null => {
      const v = rule[key];
      return typeof v === 'number' && !Number.isNaN(v) ? v : null;
    };

    if (c.program_type === 'accrual') {
      const amount = Number(this.amount());
      if (!amount || amount <= 0) return null;
      const percent = num('percent');
      if (percent !== null) return Math.floor((amount * percent) / 100);
      const ppr = num('points_per_rub');
      if (ppr !== null) return Math.floor(amount * ppr);
      return null;
    }

    const v = Math.max(1, this.visits());
    if (c.program_type === 'visit') {
      const perVisit = num('points_per_visit');
      return perVisit !== null ? v * perVisit : null;
    }
    if (c.program_type === 'stamps') {
      return v; // 1 штамп = 1 балл
    }
    return null;
  });

  ngOnDestroy(): void {
    this.stopCamera();
  }

  // ===== Сканирование =====

  async startCamera(): Promise<void> {
    this.cameraError.set(null);
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      });
      const video = this.videoRef()?.nativeElement;
      if (!video) {
        this.stopCamera();
        return;
      }
      video.srcObject = this.stream;
      await video.play();
      this.cameraOn.set(true);
      this.tick();
    } catch {
      this.cameraError.set(
        'Камера недоступна. Введите код с экрана клиента вручную.',
      );
      this.cameraOn.set(false);
    }
  }

  stopCamera(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.stream?.getTracks().forEach(t => t.stop());
    this.stream = null;
    this.cameraOn.set(false);
  }

  private tick(): void {
    const video = this.videoRef()?.nativeElement;
    if (!video || !this.cameraOn()) return;

    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      const w = video.videoWidth;
      const h = video.videoHeight;
      if (w && h) {
        this.scanCanvas.width = w;
        this.scanCanvas.height = h;
        const ctx = this.scanCanvas.getContext('2d', {
          willReadFrequently: true,
        });
        if (ctx) {
          ctx.drawImage(video, 0, 0, w, h);
          const img = ctx.getImageData(0, 0, w, h);
          const code = jsQR(img.data, w, h);
          if (code?.data) {
            const enrollmentId = parseEnrollmentCode(code.data);
            if (enrollmentId) {
              this.stopCamera();
              this.runLookup(this.pointsApi.lookup(enrollmentId));
              return;
            }
          }
        }
      }
    }
    this.rafId = requestAnimationFrame(() => this.tick());
  }

  submitManual(): void {
    const raw = this.manualCode();
    const shortCode = parseShortCode(raw);
    const enrollmentId = shortCode ? null : parseEnrollmentCode(raw);
    if (!shortCode && !enrollmentId) {
      this.notify.error('Это не похоже на код клиента');
      return;
    }
    this.stopCamera();
    this.runLookup(
      shortCode
        ? this.pointsApi.lookupByCode(shortCode)
        : this.pointsApi.lookup(enrollmentId!),
    );
  }

  private runLookup(request: Observable<EnrollmentLookup>): void {
    this.busy.set(true);
    request
      .pipe(
        catchError(err => {
          const msg =
            err?.status === 403
              ? 'Эта программа не принадлежит вашей точке'
              : err?.status === 404
                ? 'Клиент или подключение не найдены'
                : err?.error?.detail ?? 'Не удалось получить данные клиента';
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.busy.set(false)),
      )
      .subscribe(res => {
        if (res) {
          this.client.set(res);
          this.amount.set('');
          this.visits.set(1);
          this.manualPoints.set('');
          this.accrueError.set(null);
          this.stage.set('client');
        }
      });
  }

  // ===== Начисление / списание =====

  private accrueErrorMessage(err: unknown): string {
    const e = err as { status?: number; error?: { detail?: string } };
    const detail = e?.error?.detail ?? '';
    if (detail.includes('non-positive')) {
      return this.accrualMode() === 'amount'
        ? 'Сумма чека слишком мала — по правилу программы баллы не начисляются. Введите большую сумму или укажите баллы вручную.'
        : 'По правилу программы за это начислять нечего. Укажите баллы вручную.';
    }
    if (detail.includes('Program is not active')) {
      return 'Программа сейчас неактивна — начисление недоступно.';
    }
    if (detail.includes('accrual rule is misconfigured')) {
      return 'Правило начисления в программе настроено некорректно. Сообщите партнёру.';
    }
    return detail || 'Не удалось начислить баллы';
  }

  accrue(): void {
    const c = this.client();
    if (!c || this.busy()) return;
    this.accrueError.set(null);

    const body: AccruePayload = {
      customer_id: c.customer_id,
      program_id: c.program_id,
    };

    const manual = Number(this.manualPoints());
    if (this.manualPoints().trim() && manual > 0) {
      body.points = Math.floor(manual);
    } else if (this.accrualMode() === 'amount') {
      const amount = Number(this.amount());
      if (!amount || amount <= 0) {
        this.notify.error('Введите сумму чека');
        return;
      }
      body.purchase_amount = amount;
    } else {
      body.visits = Math.max(1, this.visits());
    }

    this.busy.set(true);
    this.pointsApi
      .accrue(body)
      .pipe(
        catchError(err => {
          const msg = this.accrueErrorMessage(err);
          this.accrueError.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.busy.set(false)),
      )
      .subscribe(res => {
        if (res) {
          this.done.set({
            kind: 'accrual',
            points: res.transaction.points,
            balanceAfter: res.balance_after,
            transactionId: res.transaction.id,
          });
          this.stage.set('done');
          this.notify.success(
            `Начислено ${formatPointsLabel(res.transaction.points)}`,
          );
        }
      });
  }

  redeem(reward: RewardOption): void {
    const c = this.client();
    if (!c || this.busy()) return;
    if (c.points_balance < reward.cost_points) {
      this.notify.error('Недостаточно баллов у клиента');
      return;
    }
    this.busy.set(true);
    this.pointsApi
      .redeem({
        customer_id: c.customer_id,
        program_id: c.program_id,
        reward_id: reward.id,
      })
      .pipe(
        catchError(err => {
          this.notify.error(
            err?.error?.detail ?? 'Не удалось списать баллы',
          );
          return of(null);
        }),
        finalize(() => this.busy.set(false)),
      )
      .subscribe(res => {
        if (res) {
          this.done.set({
            kind: 'redemption',
            points: res.transaction.points,
            balanceAfter: res.balance_after,
            transactionId: res.transaction.id,
          });
          this.stage.set('done');
          this.notify.success(`Награда выдана: ${reward.title}`);
        }
      });
  }

  askUndo(): void {
    if (!this.done() || this.busy()) return;
    this.confirmUndo.set(true);
  }

  cancelUndo(): void {
    this.confirmUndo.set(false);
  }

  undo(): void {
    this.confirmUndo.set(false);
    const d = this.done();
    const c = this.client();
    if (!d || this.busy()) return;
    this.busy.set(true);
    this.pointsApi
      .reverse(d.transactionId, 'Откат операции с кассы')
      .pipe(
        catchError(err => {
          this.notify.error(
            err?.status === 409
              ? 'Нельзя откатить: клиент уже потратил эти баллы'
              : err?.error?.detail ?? 'Не удалось отменить операцию',
          );
          return of(null);
        }),
        finalize(() => this.busy.set(false)),
      )
      .subscribe(res => {
        if (res) {
          this.notify.success('Операция отменена');
          if (c) {
            this.done.set(null);
            this.runLookup(this.pointsApi.lookup(c.enrollment_id));
          } else {
            this.reset();
          }
        }
      });
  }

  changeVisits(delta: number): void {
    this.visits.update(v => Math.min(99, Math.max(1, v + delta)));
  }

  reset(): void {
    this.client.set(null);
    this.done.set(null);
    this.confirmUndo.set(false);
    this.manualCode.set('');
    this.accrueError.set(null);
    this.stage.set('scan');
  }
}
