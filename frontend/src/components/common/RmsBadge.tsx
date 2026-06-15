import { Badge } from '@/components/ui/badge'

/**
 * Hata payı rozeti — bilirkişi için sade dil + değer.
 * Eşik: <5 cm "İyi" · <20 cm "Orta" · ≥20 cm "Zayıf".
 */
export function RmsBadge({ rmsM }: { rmsM: number | null | undefined }) {
  if (rmsM == null) return <Badge variant="secondary">—</Badge>
  const cm = rmsM * 100
  const variant = cm < 5 ? 'success' : cm < 20 ? 'warning' : 'danger'
  const verdict = cm < 5 ? 'İyi' : cm < 20 ? 'Orta' : 'Zayıf'
  return (
    <Badge variant={variant} title={`Hata payı: ±${cm.toFixed(1)} cm`}>
      {verdict} · ±{cm.toFixed(1)} cm
    </Badge>
  )
}
