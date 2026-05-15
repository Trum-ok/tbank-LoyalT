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
import { catchError, finalize, of } from 'rxjs';

import { PointsApi } from '../../core/api/points-api.service';
import { formatPoints, parseEnrollmentCode, programTypeLabel } from '../../core/format';
import { NotifyService } from '../../core/notify.service';

type Stage = 'scan' | 'client' | 'done';

interface DoneInfo {
  kind: 'accrual' | 'redemption';
  points: number;
  balanceAfter: number;
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
  readonly programTypeLabel = programTypeLabel;

  readonly stage = signal<Stage>('scan');
  readonly busy = signal(false);
  readonly cameraOn = signal(false);
  readonly cameraError = signal<string | null>(null);
  readonly manualCode = signal('');

  readonly client = signal<EnrollmentLookup | null>(null);
  readonly done = signal<DoneInfo | null>(null);

  // Форма начисления
  readonly amount = signal('');
  readonly visits = signal(1);
  readonly manualPoints = signal('');

  private stream: MediaStream | null = null;
  private rafId: number | null = null;
  private scanCanvas = document.createElement('canvas');

  readonly accrualMode = computed<'amount' | 'visits'>(() => {
    const c = this.client();
    return c?.program_type === 'accrual' ? 'amount' : 'visits';
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
              this.lookup(enrollmentId);
              return;
            }
          }
        }
      }
    }
    this.rafId = requestAnimationFrame(() => this.tick());
  }

  submitManual(): void {
    const enrollmentId = parseEnrollmentCode(this.manualCode());
    if (!enrollmentId) {
      this.notify.error('Это не похоже на код клиента');
      return;
    }
    this.stopCamera();
    this.lookup(enrollmentId);
  }

  private lookup(enrollmentId: string): void {
    this.busy.set(true);
    this.pointsApi
      .lookup(enrollmentId)
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
          this.stage.set('client');
        }
      });
  }

  // ===== Начисление / списание =====

  accrue(): void {
    const c = this.client();
    if (!c || this.busy()) return;

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
          this.notify.error(
            err?.error?.detail ?? 'Не удалось начислить баллы',
          );
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
          });
          this.stage.set('done');
          this.notify.success(`Начислено ${formatPoints(res.transaction.points)}`);
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
          });
          this.stage.set('done');
          this.notify.success(`Награда выдана: ${reward.title}`);
        }
      });
  }

  changeVisits(delta: number): void {
    this.visits.update(v => Math.min(99, Math.max(1, v + delta)));
  }

  reset(): void {
    this.client.set(null);
    this.done.set(null);
    this.manualCode.set('');
    this.stage.set('scan');
  }
}
