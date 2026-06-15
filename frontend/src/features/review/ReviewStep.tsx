import type { ReactNode } from 'react'
import { useWizard } from '@/store/wizard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RmsBadge } from '@/components/common/RmsBadge'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'

const LAYER_TR: Record<string, { text: string; variant: 'success' | 'warning' | 'secondary' }> = {
  operator: { text: 'Operatör onaylı', variant: 'success' },
  site_measurement: { text: 'Saha ölçümü', variant: 'success' },
  standard_assumption: { text: 'Standart varsayım', variant: 'warning' },
}

export function ReviewStep() {
  const cal = useWizard((s) => s.calibration)

  if (!cal) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Adım 4 — Kalibrasyon Sonucu</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <StatusBanner tone="warning">
            Henüz geçerli bir kalibrasyon yok. Adım 3'e dönüp en az 4 nokta girin.
          </StatusBanner>
          <StepFooter />
        </CardContent>
      </Card>
    )
  }

  const layer = LAYER_TR[cal.confidence_layer] ?? {
    text: cal.confidence_layer,
    variant: 'secondary' as const,
  }
  const redundant = cal.point_count >= 6
  const rmsOk = cal.rms_m * 100 < 5

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 4 — Kalibrasyon Sonucu</CardTitle>
        <CardDescription>
          Sonuçları bilirkişi raporuna girmeden önce kontrol edin. RMS &lt; 5 cm iyidir;
          yüksekse Adım 3'e dönüp noktaları düzeltin.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Stat label="Re-projeksiyon RMS">
            <RmsBadge rmsM={cal.rms_m} />
          </Stat>
          <Stat label="Kullanılan / Toplam nokta">
            <span className="font-semibold tabular-nums">
              {cal.inlier_count} / {cal.point_count}
            </span>
          </Stat>
          <Stat label="Güven katmanı">
            <Badge variant={layer.variant}>{layer.text}</Badge>
          </Stat>
          <Stat label="Düzlemsellik">
            {cal.planarity_warning ? (
              <Badge variant="warning">Uyarı</Badge>
            ) : (
              <Badge variant="success">Sorun yok</Badge>
            )}
          </Stat>
          <Stat label="Leave-one-out RMS">
            {cal.loo_rms_m != null ? (
              <RmsBadge rmsM={cal.loo_rms_m} label="LOO" />
            ) : (
              <span className="text-xs text-muted-foreground">Yetersiz nokta (≥5 gerekli)</span>
            )}
          </Stat>
          <Stat label="Yedeklilik (redundancy)">
            {redundant ? (
              <Badge variant="success">Yeterli (≥6)</Badge>
            ) : (
              <Badge variant="warning">Düşük ({cal.point_count})</Badge>
            )}
          </Stat>
        </div>

        {!rmsOk && (
          <StatusBanner tone="warning">
            RMS 5 cm'in üzerinde. Daha güvenilir sonuç için Adım 3'e dönüp nokta
            koordinatlarını gözden geçirin veya saha ölçümü ekleyin.
          </StatusBanner>
        )}
        {!redundant && (
          <StatusBanner tone="info">
            6'dan az kontrol noktası var. Daha fazla nokta, çapraz doğrulama (LOO) ve daha yüksek
            güven katmanı sağlar.
          </StatusBanner>
        )}

        {cal.holdout_rows.length > 0 && <HoldoutTable rows={cal.holdout_rows} />}

        <StepFooter />
      </CardContent>
    </Card>
  )
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <p className="mb-1.5 text-xs text-muted-foreground">{label}</p>
      {children}
    </div>
  )
}

function fmt(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(3)
  return String(v)
}

function HoldoutTable({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Object.keys(rows[0] ?? {})
  return (
    <div>
      <p className="mb-1 text-sm font-medium">Operatör held-out doğrulama</p>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs text-muted-foreground">
            <tr>
              {cols.map((c) => (
                <th key={c} className="px-3 py-2 text-left font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t">
                {cols.map((c) => (
                  <td key={c} className="px-3 py-1.5 font-mono text-xs">
                    {fmt(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
