import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, FileText, Loader2, Map, Ruler, RotateCcw, Target } from 'lucide-react'
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
import { SessionLogPanel } from './SessionLogPanel'
import { WheelSpeedPanel } from './WheelSpeedPanel'

export function ResultsStep() {
  const jobId = useWizard((s) => s.jobId)
  const sourceJobId = useWizard((s) => s.sourceJobId)
  const videoMeta = useWizard((s) => s.videoMeta)
  const controlPoints = useWizard((s) => s.controlPoints)
  const reset = useWizard((s) => s.reset)
  const [axleTrackId, setAxleTrackId] = useState<number | null>(null)
  const [wheelTrackId, setWheelTrackId] = useState<number | null>(null)
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
          {result.vehicle_count} araç tespit edildi. Her araç için birincil hızı ölçmek üzere
          "Hızı Ölç" butonunu kullanın — sonuç güven aralığı ve güven seviyesiyle birlikte
          rapora eklenir.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {sourceJobId && (
          <StatusBanner tone="info">
            Bu analiz aks doğrulaması eklenerek yeniden hesaplandı — tespit tekrarlanmadı, yalnızca
            kalibrasyon güncellendi. Orijinal analiz: <code className="font-mono text-xs">{sourceJobId.slice(0, 8)}…</code>
          </StatusBanner>
        )}

        {/* Araç tablosu */}
        {result.estimates.length === 0 ? (
          <StatusBanner tone="warning">
            Hız tahmini üretilemedi (yeterli/uzun takip bulunamadı). Overlay videoyu inceleyin veya
            kare adımını düşürüp tekrar deneyin.
          </StatusBanner>
        ) : (
          <>
            <StatusBanner tone="info">
              Tablo, homografi tabanlı ön tahminleri gösterir. Birincil hız için her araç satırında
              <strong> "Hızı Ölç"</strong> butonuna basın ve tekerlek temas noktasını işaretleyin.
            </StatusBanner>
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
                        Ön Tahmin (km/h)
                        <InfoHint text="Homografi tabanlı otomatik ön tahmin — yanlı olabilir (±%10). Birincil hız için 'Hızı Ölç' butonunu kullanın." />
                      </span>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <span className="flex items-center justify-end gap-1">
                        Güven Aralığı
                        <InfoHint text="±değer: ön tahmin için %95 güven aralığı yarı genişliği." />
                      </span>
                    </th>
                    <th className="px-3 py-2 font-medium">
                      <span className="flex items-center gap-1">
                        Güven
                        <InfoHint text="Tahminin genel güvenilirlik seviyesi: HIGH, MEDIUM veya LOW." />
                      </span>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <span className="flex items-center justify-end gap-1">
                        Kare
                        <InfoHint text="Bu aracın takip edildiği toplam kare sayısı. Daha fazla kare → daha güvenilir tahmin." />
                      </span>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <span className="flex items-center justify-end gap-1">
                        Aks Doğrulama
                        <InfoHint text="Aracın aks genişliğini ölçerek homografiyi çapraz doğrular." />
                      </span>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <span className="flex items-center justify-end gap-1">
                        Birincil Hız
                        <InfoHint text="Operatörün tekerlek-zemin temas noktasını elle işaretlediği birincil ölçüm. GPS doğrulamada ön tahminden ~%8 daha doğru." />
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.estimates.map((e) => (
                    <tr key={e.track_id} className="border-b last:border-0">
                      <td className="px-3 py-2 tabular-nums text-muted-foreground">#{e.track_id}</td>
                      <td className="px-3 py-2">{e.vehicle_class}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                        {e.speed_kmh.toFixed(1)}
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
                            if (wheelTrackId === e.track_id) setWheelTrackId(null)
                          }}
                        >
                          <Ruler className="size-3.5" /> Aks Doğrula
                        </Button>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          variant={wheelTrackId === e.track_id ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            setWheelTrackId(wheelTrackId === e.track_id ? null : e.track_id)
                            if (axleTrackId === e.track_id) setAxleTrackId(null)
                          }}
                        >
                          <Target className="size-3.5" /> Hızı Ölç
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
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

        {wheelTrackId != null && jobId && videoMeta && (
          <WheelSpeedPanel
            jobId={jobId}
            videoId={videoMeta.video_id}
            trackId={wheelTrackId}
            frameCount={videoMeta.frame_count}
            onClose={() => setWheelTrackId(null)}
            onReportRegenerated={() => setHasV2Report(true)}
          />
        )}

        <MethodInfoCard />

        {/* Overlay video */}
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-medium">Overlay Video</h3>
            <div className="flex flex-col items-end gap-1">
              <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground font-mono">
                Ön tahmin · Job: {jobId}
              </span>
              {sourceJobId && (
                <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700 font-medium">
                  ⟳ Yeniden kalibrasyon uygulandı (kaynak: {sourceJobId})
                </span>
              )}
            </div>
          </div>
          <video
            key={jobId}
            controls
            src={api.overlayUrl(jobId)}
            className="w-full rounded-lg border bg-canvas"
          >
            Tarayıcınız video oynatmayı desteklemiyor.
          </video>
          <p className="text-xs text-muted-foreground">
            Videodaki anlık hız değerleri ön tahmindir. Birincil hız için "Hızı Ölç" adımını kullanın.
          </p>
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

        {jobId && <SessionLogPanel jobId={jobId} />}

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
