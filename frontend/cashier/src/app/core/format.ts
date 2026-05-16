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

/**
 * Парсит код клиента: payload QR `tbank-loyalt:enrollment:<uuid>` или
 * продиктованный код. Терпим к диктовке: регистр, пробелы и отсутствие
 * дефисов игнорируются (32 hex без дефисов тоже принимаются).
 */
const QR_PREFIX = 'tbank-loyalt:enrollment:';
const HEX32_RE = /^[0-9a-f]{32}$/;

export function parseEnrollmentCode(raw: string): string | null {
  let text = raw.trim();
  const lower = text.toLowerCase();
  if (lower.startsWith(QR_PREFIX)) {
    text = text.slice(QR_PREFIX.length);
  }
  // Убираем всё кроме hex: пробелы, дефисы, переносы.
  const hex = text.toLowerCase().replace(/[^0-9a-f]/g, '');
  if (!HEX32_RE.test(hex)) return null;
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32),
  ].join('-');
}

/**
 * Короткий цифровой код подключения (4–9 цифр), продиктованный клиентом.
 * Пробелы/прочее игнорируются. null — если не похоже на код.
 */
export function parseShortCode(raw: string): string | null {
  const digits = raw.replace(/\D/g, '');
  return digits.length >= 4 && digits.length <= 9 ? digits : null;
}
