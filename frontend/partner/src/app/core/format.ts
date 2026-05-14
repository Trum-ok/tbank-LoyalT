export function formatPoints(points: number): string {
  return new Intl.NumberFormat('ru-RU').format(points);
}

export function formatAmount(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  const num = typeof value === 'string' ? Number(value) : value;
  if (Number.isNaN(num)) {
    return '—';
  }
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.valueOf())) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(d);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.valueOf())) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

export function partnerCategoryLabel(code: string): string {
  switch (code) {
    case 'food':
      return 'Кафе и еда';
    case 'beauty':
      return 'Красота';
    case 'retail':
      return 'Магазины';
    case 'services':
      return 'Услуги';
    case 'entertainment':
      return 'Развлечения';
    default:
      return code;
  }
}

export function programTypeLabel(type: string): string {
  switch (type) {
    case 'accrual':
      return 'Накопительная';
    case 'visit':
      return 'За визит';
    case 'stamps':
      return 'Штампы';
    default:
      return type;
  }
}

export function programStatusLabel(status: string): string {
  switch (status) {
    case 'draft':
      return 'черновик';
    case 'published':
      return 'опубликована';
    case 'paused':
      return 'на паузе';
    case 'archived':
      return 'архив';
    default:
      return status;
  }
}

export function applicationStatusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return 'на модерации';
    case 'approved':
      return 'одобрена';
    case 'rejected':
      return 'отклонена';
    default:
      return status;
  }
}

export function rewardTypeLabel(type: string): string {
  switch (type) {
    case 'discount_percent':
      return 'Скидка %';
    case 'discount_fixed':
      return 'Фикс. скидка';
    case 'free_item':
      return 'Бесплатный товар';
    case 'cashback_boost':
      return 'Повышенный кэшбэк';
    default:
      return type;
  }
}

export function transactionTypeLabel(type: string): string {
  switch (type) {
    case 'accrual':
      return 'Начисление';
    case 'redemption':
      return 'Списание';
    case 'reversal':
      return 'Отмена';
    default:
      return type;
  }
}
