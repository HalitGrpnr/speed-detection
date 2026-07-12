import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, FileText, Loader2, Ruler, RotateCcw } from 'lucide-react'
import { api } from '@/lib/api'
import { useWizard } from '@/store/wizard'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { MethodInfoCard } from '@/components/common/MethodInfoCard'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { AxleCheckPanel } from './AxleCheckPanel'

export function ResultsStep() {
  const jobId = useWizard((s) => s.jobId)
  const videoMeta = useWizard((s) => s.videoMeta)
  const controlPoints = useWizard((s) => s.controlPoints)
  const reset = useWizard((s) => s.reset)
  const [axleTrackId, setAxleTrackId] = useState<number | null>(null)

  const resultsQuery = useQuery({
    queryKey: ['jobResults', jobId],
    queryFn: () => api.jobResults(jobId!),
    enabled: !!jobId,
  })

  if (!jobId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Adım 6 — Sonuçlar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <StatusBanner tone="warning">
            Henüz tamamlanmış bir analiz yok. Önce Adım 5'te analizi çalıştırın.
          </StatusBanner>
          <StepFooter />
        </CardContent>
      </Card>
    )
  }

  if (resultsQuery.isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Adım 6 — Sonuçlar</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin text-primary" /> Sonuçlar yükleniyor…
          </div>
        </CardContent>
      </Card>
    )
  }

  if (resultsQuery.isError || !resultsQuery.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Adım 6 — Sonuçlar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <StatusBanner tone="error">
            {(resultsQuery.error as Error)?.message ?? 'Sonuçlar alınamadı.'}
          </StatusBanner>
          <StepFooter />
        </CardContent>
      </Card>
    )
  }

  const result = resultsQuery.data

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 6 — Sonuçlar</CardTitle>
        <CardDescription>
          {result.vehicle_count} araç için hız tahmini. Her değer güven aralığı (±) ve güven
          seviyesiyle birlikte verilir — çıplak sayı sunulmaz.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Hız tablosu */}
        {result.estimates.length === 0 ? (
          <StatusBanner tone="warning">
            Hız tahmini üretilemedi (yeterli/uzun takip bulunamadı). Overlay videoyu inceleyin veya
            kare adımını düşürüp tekrar deneyin.
          </StatusBanner>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-left text-xs uppercase text-muted-foreground">
                  <th className="px-3 py-2 font-medium">Takip</th>
                  <th className="px-3 py-2 font-medium">Sınıf</th>
                  <th className="px-3 py-2 text-right font-medium">Hız (km/h)</th>
                  <th className="px-3 py-2 text-right font-medium">Güven Aralığı</th>
                  <th className="px-3 py-2 font-medium">Güven</th>
                  <th className="px-3 py-2 text-right font-medium">Kare</th>
                  <th className="px-3 py-2 text-right font-medium">Ek Doğrulama</th>
                </tr>
              </thead>
              <tbody>
                {result.estimates.map((e) => (
                  <tr key={e.track_id} className="border-b last:border-0">
                    <td className="px-3 py-2 tabular-nums text-muted-foreground">#{e.track_id}</td>
                    <td className="px-3 py-2">{e.vehicle_class}</td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-base font-semibold tabular-nums">
                        {e.speed_kmh.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      ± {e.ci_kmh.toFixed(1)}
                    </td>
                    <td className="px-3 py-2">
                      <ConfidenceBadge level={e.confidence_level} />
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      {e.frame_count}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setAxleTrackId(axleTrackId === e.track_id ? null : e.track_id)
                        }
                      >
                        <Ruler className="size-3.5" /> Aks Doğrula
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {axleTrackId != null && jobId && videoMeta && (
          <AxleCheckPanel
            jobId={jobId}
            videoId={videoMeta.video_id}
            trackId={axleTrackId}
            controlPoints={controlPoints}
            onClose={() => setAxleTrackId(null)}
          />
        )}

        <MethodInfoCard />

        {/* Overlay video */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Overlay Video</h3>
          <video
            controls
            src={api.overlayUrl(jobId)}
            className="w-full rounded-lg border bg-canvas"
          >
            Tarayıcınız video oynatmayı desteklemiyor.
          </video>
        </div>

        {/* İndirmeler */}
        <div className="flex flex-wrap gap-3">
          <a href={api.reportUrl(jobId)} download className={buttonVariants({ variant: 'outline' })}>
            <FileText /> PDF Raporu İndir
          </a>
          <a
            href={api.overlayDownloadUrl(jobId)}
            download
            className={buttonVariants({ variant: 'outline' })}
          >
            <Download /> Overlay Video İndir
          </a>
        </div>

        <Separator />

        <div className="flex items-center justify-between">
          <Button variant="secondary" onClick={() => useWizard.getState().back()}>
            ← Geri
          </Button>
          <Button variant="success" onClick={reset}>
            <RotateCcw /> Yeni Analiz
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
