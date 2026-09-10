import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, FileText, Loader2, Map, Milestone, Ruler, RotateCcw } from 'lucide-react'
import { api } from '@/lib/api'
import { useWizard } from '@/store/wizard'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { MethodInfoCard } from '@/components/common/MethodInfoCard'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { InfoHint } from '@/components/common/InfoHint'
import { AxleCheckPanel } from './AxleCheckPanel'
import { AxleSteppingPanel } from './AxleSteppingPanel'

export function ResultsStep() {
  const jobId = useWizard((s) => s.jobId)
  const sourceJobId = useWizard((s) => s.sourceJobId)
  const videoMeta = useWizard((s) => s.videoMeta)
  const controlPoints = useWizard((s) => s.controlPoints)
  const reset = useWizard((s) => s.reset)
  const [axleTrackId, setAxleTrackId] = useState<number | null>(null)
  const [steppingTrackId, setSteppingTrackId] = useState<number | null>(null)
  const [showPlanView, setShowPlanView] = useState(false)
  const [hasV2Report, setHasV2Report] = useState(false)

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
        {sourceJobId && (
          <StatusBanner tone="info">
            Bu analiz aks doğrulaması eklenerek yeniden hesaplandı — tespit tekrarlanmadı, yalnızca
            kalibrasyon güncellendi. Orijinal analiz: <code className="font-mono text-xs">{sourceJobId.slice(0, 8)}…</code>
          </StatusBanner>
        )}

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
                  <th className="px-3 py-2 font-medium">
                    <span className="flex items-center gap-1">
                      Takip
                      <InfoHint text="ByteTrack tarafından aynı fiziksel araca atanan benzersiz kimlik numarası. Her analiz çalıştırmasında sıfırdan başlar." />
                    </span>
                  </th>
                  <th className="px-3 py-2 font-medium">
                    <span className="flex items-center gap-1">
                      Sınıf
                      <InfoHint text="YOLO modelinin tespit ettiği araç türü (car, truck, bus, motorcycle vb.)." />
                    </span>
                  </th>
                  <th className="px-3 py-2 text-right font-medium">
                    <span className="flex items-center justify-end gap-1">
                      Hız (km/h)
                      <InfoHint text="Aracın tekerlek-zemin temas noktasının homografi üzerinden dünya koordinatlarındaki ortalama hızı. Bbox merkezi değil temas noktası kullanılır — paralaks hatasını önler." />
                    </span>
                  </th>
                  <th className="px-3 py-2 text-right font-medium">
                    <span className="flex items-center justify-end gap-1">
                      Güven Aralığı
                      <InfoHint text="±değer: hız tahmininin %95 güven aralığı yarı genişliği. Takip boyunca ölçüm tutarsızlığından (kare-kare varyans) ve kalibrasyon belirsizliğinden hesaplanır. Daha dar = daha tutarlı ölçüm." />
                    </span>
                  </th>
                  <th className="px-3 py-2 font-medium">
                    <span className="flex items-center gap-1">
                      Güven
                      <InfoHint text="Tahminin genel güvenilirlik seviyesi: HIGH (kısa güven aralığı, uzun takip), MEDIUM veya LOW. Bilirkişi raporuna yansır." />
                    </span>
                  </th>
                  <th className="px-3 py-2 text-right font-medium">
                    <span className="flex items-center justify-end gap-1">
                      Kare
                      <InfoHint text="Bu aracın takip edildiği toplam kare sayısı. Daha fazla kare → daha güvenilir hız tahmini. Çok kısa takipler (genellikle &lt;5 kare) raporlanmaz." />
                    </span>
                  </th>
                  <th className="px-3 py-2 text-right font-medium">
                    <span className="flex items-center justify-end gap-1">
                      Aks Doğrulama
                      <InfoHint text="Aracın aks genişliğini ölçerek homografiyi çapraz doğrular. Bilinen araç genişliğiyle karşılaştırılır; büyük sapma kalibrasyon sorununa işaret eder." />
                    </span>
                  </th>
                  <th className="px-3 py-2 text-right font-medium">
                    <span className="flex items-center justify-end gap-1">
                      Dingil Adımlama
                      <InfoHint text="Ön/arka teker adımı ile bağımsız hız tahmini. Araç kendi tekerleklerini referans alır, harici nokta gerekmez. H-tabanlı hızla karşılaştırma üretir." />
                    </span>
                  </th>
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
                        onClick={() => {
                          setAxleTrackId(axleTrackId === e.track_id ? null : e.track_id)
                          if (steppingTrackId === e.track_id) setSteppingTrackId(null)
                        }}
                      >
                        <Ruler className="size-3.5" /> Aks Doğrula
                      </Button>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSteppingTrackId(steppingTrackId === e.track_id ? null : e.track_id)
                          if (axleTrackId === e.track_id) setAxleTrackId(null)
                        }}
                      >
                        <Milestone className="size-3.5" /> Dingil
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
            onReportRegenerated={() => setHasV2Report(true)}
          />
        )}

        {steppingTrackId != null && jobId && videoMeta && (
          <AxleSteppingPanel
            jobId={jobId}
            videoId={videoMeta.video_id}
            trackId={steppingTrackId}
            onClose={() => setSteppingTrackId(null)}
          />
        )}

        <MethodInfoCard />

        {/* Overlay video */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Overlay Video</h3>
          <video
            key={jobId}
            controls
            src={api.overlayUrl(jobId)}
            className="w-full rounded-lg border bg-canvas"
          >
            Tarayıcınız video oynatmayı desteklemiyor.
          </video>
        </div>

        {/* Kuş bakışı */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPlanView((v) => !v)}
            >
              <Map className="size-3.5" />
              {showPlanView ? 'Kuş Bakışını Gizle' : 'Kuş Bakışını Göster'}
            </Button>
            {showPlanView && (
              <span className="text-xs text-muted-foreground">
                1 m'lik ızgara üzerinde araçları ölçerek homografiyi doğrulayabilirsiniz.
              </span>
            )}
          </div>
          {showPlanView && (
            <img
              src={api.jobPlanViewUrl(jobId)}
              alt="Kuş bakışı (plan view)"
              className="w-full rounded-lg border"
            />
          )}
        </div>

        {/* İndirmeler */}
        <div className="flex flex-wrap gap-3">
          <a href={api.reportUrl(jobId)} download className={buttonVariants({ variant: 'outline' })}>
            <FileText /> PDF Raporu İndir
          </a>
          {hasV2Report && jobId && (
            <a href={api.reportV2Url(jobId)} download className={buttonVariants({ variant: 'default' })}>
              <FileText /> Güncellenmiş Raporu İndir (v2)
            </a>
          )}
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
