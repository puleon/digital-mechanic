import type { SessionStatus } from './types'

export interface StatusInfo {
  text: string
  tone: 'ok' | 'warn' | 'danger' | 'muted'
}

export function statusInfo(status?: SessionStatus | null): StatusInfo {
  switch (status) {
    case 'normal':
      return { text: 'Норма', tone: 'ok' }
    case 'anomaly':
      return { text: 'Отклонение', tone: 'danger' }
    case 'check_failed':
      return { text: 'Сбой записи', tone: 'muted' }
    default:
      return { text: 'Нет данных', tone: 'muted' }
  }
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatScore(value?: number | null): string {
  return value === null || value === undefined ? '—' : value.toFixed(2)
}

export function formatConfidence(value?: number | null): string {
  return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`
}

/** Русская форма множественного числа: plural(3, ['проверка', 'проверки', 'проверок']). */
export function plural(count: number, forms: [string, string, string]): string {
  const mod100 = Math.abs(count) % 100
  const mod10 = mod100 % 10
  if (mod100 > 10 && mod100 < 20) return forms[2]
  if (mod10 === 1) return forms[0]
  if (mod10 >= 2 && mod10 <= 4) return forms[1]
  return forms[2]
}
