export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('ru-RU').format(value);
}

export function formatPoints(points: number): string {
  return new Intl.NumberFormat('ru-RU').format(points);
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
      return 'Еда и напитки';
    case 'beauty':
      return 'Красота и здоровье';
    case 'retail':
      return 'Розница';
    case 'services':
      return 'Услуги';
    case 'entertainment':
      return 'Развлечения';
    default:
      return code;
  }
}

export function partnerCategoriesLabel(
  codes: string[] | null | undefined,
): string {
  if (!codes || codes.length === 0) return '—';
  return codes.map(partnerCategoryLabel).join(', ');
}

export function partnerStatusLabel(status: string): string {
  switch (status) {
    case 'active':
      return 'активен';
    case 'suspended':
      return 'приостановлен';
    case 'blocked':
      return 'заблокирован';
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
