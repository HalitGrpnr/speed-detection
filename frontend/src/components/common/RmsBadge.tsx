import { Badge } from '@/components/ui/badge'

/**
 * Re-projeksiyon RMS rozeti. Eşik: <5 cm iyi · <20 cm orta · ≥20 cm kötü.
 * (Legacy app.js renk eşikleriyle hizalı.)
 */
export function RmsBadge({ rmsM, label = 'RMS' }: { rmsM: number | null | undefined; label?: string }) {
  if (rmsM == null) return <Badge variant="secondary">{label} —</Badge>
  const cm = rmsM * 100
  const variant = cm < 5 ? 'success' : cm < 20 ? 'warning' : 'danger'
  return (
    <Badge variant={variant}>
      {label} {cm.toFixed(1)} cm
    </Badge>
  )
}
