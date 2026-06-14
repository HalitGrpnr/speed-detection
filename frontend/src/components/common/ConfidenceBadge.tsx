import { Badge } from '@/components/ui/badge'

const LABELS: Record<string, { text: string; variant: 'success' | 'warning' | 'danger' }> = {
  high: { text: 'Yüksek güven', variant: 'success' },
  medium: { text: 'Orta güven', variant: 'warning' },
  low: { text: 'Düşük güven', variant: 'danger' },
}

/** Güven seviyesi rozeti (CLAUDE.md kural 4: hız asla çıplak sayı değildir). */
export function ConfidenceBadge({ level }: { level: string }) {
  const m = LABELS[level]
  if (!m) return <Badge variant="secondary">{level}</Badge>
  return <Badge variant={m.variant}>{m.text}</Badge>
}
