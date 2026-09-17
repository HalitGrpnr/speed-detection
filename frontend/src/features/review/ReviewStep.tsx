import type { ReactNode } from 'react'
import { useWizard } from '@/store/wizard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { InfoHint } from '@/components/common/InfoHint'
import { RmsBadge } from '@/components/common/RmsBadge'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { PlanViewPreview } from './PlanViewPreview'

const LAYER_TR: Record<string, { text: string; variant: 'success' | 'warning' | 'secondary' }> = {
  operator: { text: 'Operatör onaylı', variant: 'success' },
  site_measurement: { text: 'Saha ölçümü', variant: 'success' },
  standard_assumption: { text: 'Standart varsayım', variant: 'warning' },
}

export function ReviewStep() {
  const cal = useWizard((s) => s.calibration)
  const videoMeta = useWizard((s) => s.videoMeta)
  const selectedFrame = useWizard((s) => s.selectedFrame)
  const controlPoints = useWizard((s) => s.controlPoints)

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
          Sonuçları bilirkişi raporuna girmeden önce kontrol edin. Hata payı 5 cm'in
          altındaysa iyidir; yüksekse Adım 3'e dönüp noktaları düzeltin.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Birincil metrik — tam genişlik, öne çıkan kart */}
        <div className={`rounded-lg border p-4 ${rmsOk ? 'border-success/40 bg-success/5' : 'border-warning/40 bg-warning/5'}`}>
          <p className="mb-2 text-xs text-muted-foreground flex items-center gap-1.5">
            Kalibrasyon hata payı
            <InfoHint text="Tıkladığınız noktaların girdiğiniz ölçümlerle ne kadar uyuştuğu. Küçük olması iyidir. (Teknik: re-projeksiyon RMS)" />
          </p>
          <RmsBadge rmsM={cal.rms_m} />
          <p className="text-xs text-muted-foreground mt-1.5">
            {cal.inlier_count}/{cal.point_count} nokta kullanıldı
            {cal.rejected_points.length > 0 && (
              <span className="text-orange-500 ml-1">· {cal.rejected_points.length} reddedildi</span>
            )}
          </p>
        </div>

        {/* Diğer metrikler — 2-3 sütun grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Stat
            label="Güven kaynağı"
            hint="Kalibrasyonun hangi referansa dayandığı (operatör onayı, saha ölçümü veya standart varsayım)."
          >
            <Badge variant={layer.variant}>{layer.text}</Badge>
          </Stat>
          <Stat
            label="Zemin düzlemi"
            hint="Tüm noktalar tek bir düz zeminde mi? Değilse (kaldırım, eğim) sonuç bozulabilir."
          >
            {cal.planarity_warning ? (
              <Badge variant="warning">Aynı düzlemde değil</Badge>
            ) : (
              <Badge variant="success">Sorun yok</Badge>
            )}
          </Stat>
          <Stat
            label="Bağımsız doğrulama"
            hint="Bir noktayı dışarıda bırakıp geri kalanla tahmin ederek doğruluğu sınar. (Teknik: leave-one-out RMS)"
          >
            {cal.loo_rms_m != null ? (
              <RmsBadge rmsM={cal.loo_rms_m} />
            ) : (
              <span className="text-xs text-muted-foreground">≥5 nokta gerekli</span>
            )}
          </Stat>
          <Stat
            label="Nokta yeterliliği"
            hint="Güvenilir kontrol için fazladan nokta var mı? 6 ve üzeri önerilir."
          >
            {redundant ? (
              <Badge variant="success">Yeterli (≥6)</Badge>
            ) : (
              <Badge variant="warning">Düşük ({cal.point_count})</Badge>
            )}
          </Stat>
        </div>

        {/* Karar özeti */}
        <div className={`rounded-lg border p-4 ${rmsOk && redundant ? 'border-success/40 bg-success/5' : rmsOk ? 'border-primary/30 bg-primary/5' : 'border-warning/40 bg-warning/5'}`}>
          <p className={`text-sm font-medium ${rmsOk && redundant ? 'text-success' : rmsOk ? 'text-primary' : 'text-warning'}`}>
            {rmsOk && redundant
              ? '✓ Kalibrasyon analize hazır'
              : rmsOk
                ? '✓ Kalibrasyon yeterli — Daha fazla nokta güveni artırır'
                : '⚠ Analiz başlamadan önce kontrol edin'}
          </p>
          <p className="text-xs text-muted-foreground mt-1 tabular-nums">
            RMS: {(cal.rms_m * 100).toFixed(1)} cm
            {' · '}{cal.inlier_count}/{cal.point_count} nokta
            {' · '}Yedeklilik: {redundant ? 'Yeterli' : 'Düşük'}
            {cal.planarity_warning ? ' · ⚠ Düzlemsellik sorunu' : ''}
          </p>
        </div>

        {cal.holdout_rows.length > 0 && <HoldoutTable rows={cal.holdout_rows} />}

        {videoMeta && (
          <PlanViewPreview
            videoId={videoMeta.video_id}
            frame={selectedFrame}
            controlPoints={controlPoints}
          />
        )}

        <StepFooter />
      </CardContent>
    </Card>
  )
}

function Stat({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <p className="mb-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
        {label}
        {hint && <InfoHint text={hint} />}
      </p>
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
      <p className="mb-1 flex items-center gap-1.5 text-sm font-medium">
        Ayrı tutulan noktalarla doğrulama
        <InfoHint text="Bilerek dışarıda bıraktığınız noktaların, kalan noktalarla kurulan modelle ne kadar doğru tahmin edildiği." />
      </p>
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
