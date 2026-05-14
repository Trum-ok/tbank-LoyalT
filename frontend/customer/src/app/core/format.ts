const RU_DATE = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

const RU_DATETIME = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return RU_DATE.format(new Date(iso));
  } catch {
    return iso ?? '';
  }
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return RU_DATETIME.format(new Date(iso));
  } catch {
    return iso ?? '';
  }
}

export function formatPoints(value: number, signed = false): string {
  const formatted = new Intl.NumberFormat('ru-RU').format(Math.abs(value));
  if (!signed) return formatted;
  return value >= 0 ? `+${formatted}` : `−${formatted}`;
}
