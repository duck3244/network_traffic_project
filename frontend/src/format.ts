export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let v = n / 1024
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(v >= 10 ? 1 : 2)} ${units[i]}`
}

export function formatNumber(n: number, digits = 2): string {
  if (!Number.isFinite(n)) return String(n)
  const abs = Math.abs(n)
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(digits)}B`
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(digits)}M`
  if (abs >= 1_000) return `${(n / 1_000).toFixed(digits)}K`
  if (abs >= 1) return n.toFixed(digits)
  if (abs === 0) return '0'
  return n.toFixed(4)
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

export function formatDateTimeShort(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const DAY_LABELS = ['월', '화', '수', '목', '금', '토', '일']
export function dayLabel(idx: number): string {
  return DAY_LABELS[idx] ?? String(idx)
}
