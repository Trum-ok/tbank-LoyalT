import { Component, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  ProgramRead,
  ProgramUpdate,
  RewardCreate,
  RewardRead,
  RewardType,
  TierCreate,
  TierRead,
  TierUpdate,
} from '@tbank-loyalt/shared';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import { ProgramsApi } from '../../core/api/programs-api.service';
import { RewardsApi } from '../../core/api/rewards-api.service';
import {
  formatDate,
  programStatusLabel,
  programTypeLabel,
  rewardTypeLabel,
} from '../../core/format';
import { NotifyService } from '../../core/notify.service';

const REWARD_TYPE_OPTIONS: { code: RewardType; label: string; hint: string }[] = [
  { code: 'discount_percent', label: 'Скидка %', hint: 'процент от чека' },
  { code: 'discount_fixed', label: 'Фикс. скидка', hint: 'минус N рублей' },
  { code: 'free_item', label: 'Бесплатный товар', hint: 'позиция в подарок' },
  { code: 'cashback_boost', label: 'Boost кэшбэка', hint: 'повышенный процент' },
];

interface RewardDraft {
  title: string;
  description: string;
  cost_points: number;
  type: RewardType;
  amount: number;
  item: string;
}

interface ProgramForm {
  name: string;
  description: string;
  percent: number | null;
  points_per_visit: number | null;
  visits_required: number | null;
  points_ttl_days: number | null;
  expire_warn_days: number | null;
  min_redemption: number;
  // Бонусные механики
  welcome_bonus_points: number | null;
  birthday_bonus_points: number | null;
  birthday_bonus_days: number;
  referral_bonus_points: number | null;
  // Ограничения
  min_purchase_rub: number | null;
  max_points_per_transaction: number | null;
  max_redemption_percent: number | null;
  // Период действия
  valid_from: string;
  valid_until: string;
}

interface TierDraft {
  name: string;
  threshold_points: number;
  accrual_multiplier: number;
}

@Component({
  selector: 'app-program-detail-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './program-detail-page.html',
  styleUrl: './program-detail-page.scss',
})
export class ProgramDetailPage {
  readonly id = input.required<string>();

  private readonly programsApi = inject(ProgramsApi);
  private readonly rewardsApi = inject(RewardsApi);
  private readonly router = inject(Router);
  private readonly notify = inject(NotifyService);

  readonly rewardTypeOptions = REWARD_TYPE_OPTIONS;
  readonly programTypeLabel = programTypeLabel;
  readonly programStatusLabel = programStatusLabel;
  readonly rewardTypeLabel = rewardTypeLabel;
  readonly formatDate = formatDate;

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly program = signal<ProgramRead | null>(null);
  readonly rewards = signal<RewardRead[]>([]);
  readonly form = signal<ProgramForm | null>(null);
  readonly saving = signal(false);
  readonly transitionPending = signal<string | null>(null);

  readonly rewardCreatorOpen = signal(false);
  readonly creatingReward = signal(false);
  readonly rewardDraft = signal<RewardDraft>(this.defaultRewardDraft());

  // Tier management
  readonly tierModalOpen = signal(false);
  readonly editingTierId = signal<string | null>(null);
  readonly tierDraft = signal<TierDraft>(this.defaultTierDraft());
  readonly tierPending = signal(false);

  readonly canPublish = computed(() => {
    const p = this.program();
    return p?.status === 'draft' || p?.status === 'paused';
  });
  readonly canPause = computed(() => this.program()?.status === 'published');
  readonly canArchive = computed(() => {
    const s = this.program()?.status;
    return s === 'paused' || s === 'draft';
  });
  readonly isArchived = computed(() => this.program()?.status === 'archived');

  constructor() {
    queueMicrotask(() => this.reload());
  }

  private reload(): void {
    const id = this.id();
    if (!id) return;
    this.loading.set(true);
    this.error.set(null);

    forkJoin({
      program: this.programsApi.get(id).pipe(catchError(() => of(null))),
      rewards: this.rewardsApi.list(id).pipe(catchError(() => of([] as RewardRead[]))),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ program, rewards }) => {
        this.program.set(program);
        this.rewards.set(rewards);
        if (program) {
          this.form.set(this.formFromProgram(program));
        }
      });
  }

  patch<K extends keyof ProgramForm>(key: K, value: ProgramForm[K]): void {
    this.form.update(f => (f ? { ...f, [key]: value } : f));
  }

  save(): void {
    const p = this.program();
    const f = this.form();
    if (!p || !f) return;

    const update: ProgramUpdate = {
      name: f.name,
      description: f.description || null,
      accrual_rule: this.buildRule(p, f),
      points_ttl_days: f.points_ttl_days,
      expire_warn_days: f.points_ttl_days ? f.expire_warn_days : null,
      min_redemption: f.min_redemption,
      welcome_bonus_points: f.welcome_bonus_points,
      birthday_bonus_points: f.birthday_bonus_points,
      birthday_bonus_days: f.birthday_bonus_days,
      referral_bonus_points: f.referral_bonus_points,
      min_purchase_amount:
        f.min_purchase_rub != null ? Math.round(f.min_purchase_rub * 100) : null,
      max_points_per_transaction: f.max_points_per_transaction,
      max_redemption_percent: f.max_redemption_percent,
      valid_from: f.valid_from || null,
      valid_until: f.valid_until || null,
    };

    this.saving.set(true);
    this.error.set(null);
    this.programsApi
      .update(p.id, update)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось сохранить';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
      )
      .subscribe(updated => {
        if (updated) {
          this.program.set(updated);
          this.form.set(this.formFromProgram(updated));
          this.notify.success('Изменения программы сохранены');
        }
      });
  }

  publish(): void {
    this.transition('publish', 'Программа опубликована', id =>
      this.programsApi.publish(id),
    );
  }

  pause(): void {
    this.transition('pause', 'Программа поставлена на паузу', id =>
      this.programsApi.pause(id),
    );
  }

  archive(): void {
    this.transition('archive', 'Программа отправлена в архив', id =>
      this.programsApi.archive(id),
    );
  }

  // ── Rewards ────────────────────────────────────────────────────────────────

  openRewardCreator(): void {
    this.rewardDraft.set(this.defaultRewardDraft());
    this.rewardCreatorOpen.set(true);
  }

  closeRewardCreator(): void {
    this.rewardCreatorOpen.set(false);
  }

  patchReward<K extends keyof RewardDraft>(key: K, value: RewardDraft[K]): void {
    this.rewardDraft.update(d => ({ ...d, [key]: value }));
  }

  createReward(): void {
    const p = this.program();
    if (!p) return;

    const d = this.rewardDraft();
    if (!d.title.trim() || d.cost_points <= 0) {
      this.error.set('Название и стоимость награды обязательны');
      return;
    }

    const body: RewardCreate = {
      title: d.title.trim(),
      description: d.description.trim() || null,
      cost_points: d.cost_points,
      type: d.type,
      value: this.buildRewardValue(d),
      is_active: true,
    };

    this.creatingReward.set(true);
    this.error.set(null);
    this.rewardsApi
      .create(p.id, body)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось создать награду';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.creatingReward.set(false)),
      )
      .subscribe(r => {
        if (r) {
          this.rewards.update(rs => [...rs, r]);
          this.closeRewardCreator();
          this.notify.success(`Награда «${r.title}» добавлена`);
        }
      });
  }

  toggleReward(r: RewardRead): void {
    this.rewardsApi
      .update(r.id, { is_active: !r.is_active })
      .pipe(
        catchError(err => {
          this.notify.error(err?.error?.detail ?? 'Не удалось обновить награду');
          return of(null);
        }),
      )
      .subscribe(updated => {
        if (updated) {
          this.rewards.update(rs => rs.map(x => (x.id === updated.id ? updated : x)));
          this.notify.success(
            updated.is_active
              ? `Награда «${updated.title}» снова активна`
              : `Награда «${updated.title}» отключена`,
          );
        }
      });
  }

  rewardValueSummary(r: RewardRead): string {
    const v = r.value as Record<string, number | string>;
    switch (r.type) {
      case 'discount_percent':
        return `-${v['percent'] ?? '?'}% от чека`;
      case 'discount_fixed':
        return `-${v['amount'] ?? '?'} ₽`;
      case 'free_item':
        return String(v['item'] ?? 'позиция в подарок');
      case 'cashback_boost':
        return `+${v['percent'] ?? '?'}% кэшбэка`;
    }
  }

  // ── Tiers ──────────────────────────────────────────────────────────────────

  openTierCreator(): void {
    this.editingTierId.set(null);
    this.tierDraft.set(this.defaultTierDraft());
    this.tierModalOpen.set(true);
  }

  openTierEditor(tier: TierRead): void {
    this.editingTierId.set(tier.id);
    this.tierDraft.set({
      name: tier.name,
      threshold_points: tier.threshold_points,
      accrual_multiplier: tier.accrual_multiplier,
    });
    this.tierModalOpen.set(true);
  }

  closeTierModal(): void {
    this.tierModalOpen.set(false);
  }

  patchTier<K extends keyof TierDraft>(key: K, value: TierDraft[K]): void {
    this.tierDraft.update(d => ({ ...d, [key]: value }));
  }

  saveTier(): void {
    const p = this.program();
    if (!p) return;

    const d = this.tierDraft();
    if (!d.name.trim()) {
      this.notify.error('Укажите название уровня');
      return;
    }

    this.tierPending.set(true);
    const editId = this.editingTierId();

    const request$ = editId
      ? this.programsApi.updateTier(p.id, editId, {
          name: d.name.trim(),
          threshold_points: d.threshold_points,
          accrual_multiplier: d.accrual_multiplier,
        } satisfies TierUpdate)
      : this.programsApi.addTier(p.id, {
          name: d.name.trim(),
          threshold_points: d.threshold_points,
          accrual_multiplier: d.accrual_multiplier,
        } satisfies TierCreate);

    request$
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось сохранить уровень';
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.tierPending.set(false)),
      )
      .subscribe(updated => {
        if (updated) {
          this.program.set(updated);
          this.closeTierModal();
          this.notify.success(editId ? 'Уровень обновлён' : 'Уровень добавлен');
        }
      });
  }

  deleteTier(tier: TierRead): void {
    const p = this.program();
    if (!p) return;

    this.programsApi
      .deleteTier(p.id, tier.id)
      .pipe(
        catchError(err => {
          this.notify.error(err?.error?.detail ?? 'Не удалось удалить уровень');
          return of(null);
        }),
      )
      .subscribe(updated => {
        if (updated) {
          this.program.set(updated);
          this.notify.success(`Уровень «${tier.name}» удалён`);
        }
      });
  }

  tierMultiplierLabel(m: number): string {
    return m === 1 ? 'базовый' : `×${m}`;
  }

  // ── Private ────────────────────────────────────────────────────────────────

  private transition(
    name: string,
    successMessage: string,
    fn: (id: string) => ReturnType<ProgramsApi['publish']>,
  ): void {
    const p = this.program();
    if (!p) return;
    this.transitionPending.set(name);
    fn(p.id)
      .pipe(
        catchError(err => {
          const msg = err?.error?.detail ?? 'Не удалось обновить статус';
          this.error.set(msg);
          this.notify.error(msg);
          return of(null);
        }),
        finalize(() => this.transitionPending.set(null)),
      )
      .subscribe(updated => {
        if (updated) {
          this.program.set(updated);
          this.notify.success(successMessage);
        }
      });
  }

  private buildRule(p: ProgramRead, f: ProgramForm): Record<string, unknown> {
    switch (p.type) {
      case 'accrual':
        return { percent: f.percent ?? 0 };
      case 'visit':
        return { points_per_visit: f.points_per_visit ?? 0 };
      case 'stamps':
        return { visits_required: f.visits_required ?? 0 };
    }
  }

  private buildRewardValue(d: RewardDraft): Record<string, unknown> {
    switch (d.type) {
      case 'discount_percent':
      case 'cashback_boost':
        return { percent: d.amount };
      case 'discount_fixed':
        return { amount: d.amount };
      case 'free_item':
        return { item: d.item || 'free' };
    }
  }

  private defaultRewardDraft(): RewardDraft {
    return {
      title: '',
      description: '',
      cost_points: 100,
      type: 'discount_percent',
      amount: 10,
      item: '',
    };
  }

  private defaultTierDraft(): TierDraft {
    return { name: '', threshold_points: 0, accrual_multiplier: 1.0 };
  }

  private formFromProgram(p: ProgramRead): ProgramForm {
    const rule = p.accrual_rule as Record<string, number>;
    return {
      name: p.name,
      description: p.description ?? '',
      percent: rule['percent'] ?? null,
      points_per_visit: rule['points_per_visit'] ?? null,
      visits_required: rule['visits_required'] ?? null,
      points_ttl_days: p.points_ttl_days,
      expire_warn_days: p.expire_warn_days,
      min_redemption: p.min_redemption,
      welcome_bonus_points: p.welcome_bonus_points,
      birthday_bonus_points: p.birthday_bonus_points,
      birthday_bonus_days: p.birthday_bonus_days ?? 0,
      referral_bonus_points: p.referral_bonus_points,
      min_purchase_rub:
        p.min_purchase_amount != null ? p.min_purchase_amount / 100 : null,
      max_points_per_transaction: p.max_points_per_transaction,
      max_redemption_percent: p.max_redemption_percent,
      valid_from: p.valid_from ?? '',
      valid_until: p.valid_until ?? '',
    };
  }
}
