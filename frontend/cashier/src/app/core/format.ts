export function formatPoints(points: number): string {
  return new Intl.NumberFormat('ru-RU').format(points);
}

/** Падежная форма слова «балл»: 1 балл, 2 балла, 5 баллов. */
export function pointsWord(points: number): string {
  const n = Math.abs(Math.trunc(points)) % 100;
  if (n >= 11 && n <= 14) return 'баллов';
  switch (n % 10) {
    case 1:
      return 'балл';
    case 2:
    case 3:
    case 4:
      return 'балла';
    default:
      return 'баллов';
  }
}

/** «1 234 балла» — число + согласованное слово. */
export function formatPointsLabel(points: number): string {
  return `${formatPoints(points)} ${pointsWord(points)}`;
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

export function transactionTypeLabel(type: string): string {
  switch (type) {
    case 'accrual':
      return 'Начисление';
    case 'redemption':
      return 'Списание';
    case 'reversal':
      return 'Отмена';
    case 'expiration':
      return 'Сгорание';
    default:
      return type;
  }
}

/** Парсит payload QR клиента: `tbank-loyalt:enrollment:<uuid>`. */
const QR_PREFIX = 'tbank-loyalt:enrollment:';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function parseEnrollmentCode(raw: string): string | null {
  const text = raw.trim();
  const candidate = text.startsWith(QR_PREFIX)
    ? text.slice(QR_PREFIX.length)
    : text;
  return UUID_RE.test(candidate) ? candidate.toLowerCase() : null;
}
