import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, FileText, Loader2, Map, Ruler, RotateCcw, Target } from 'lucide-react'
import { api } from '@/lib/api'
import type { WheelSpeedResponse } from '@/lib/models'
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
  // T21: Track başına tekerlek hız sonuçları
  const [wheelSpeedResults, setWheelSpeedResults] = useState<Record<number, WheelSpeedResponse>>({})
  // T21: Rapor indirme uyarı modal
  const [showReportWarning, setShowReportWarning] = useState(false)
  const [pendingDownloadUrl, setPendingDownloadUrl] = useState<string | null>(null)
  // T25: Tekerlek overlay hazır olan track'ler + aktif overlay seçimi
  const [wheelOverlayTracks, setWheelOverlayTracks] = useState<Set<number>>(new Set())
  const [activeOverlay, setActiveOverlay] = useState<'bbox' | number>('bbox')

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

  // T21: Tekerlek hız sonucunu kaydet
  const handleWheelSpeedResult = (trackId: number, res: WheelSpeedResponse) => {
    setWheelSpeedResults((prev) => ({ ...prev, [trackId]: res }))
  }

  // T21: PDF indirme — tekerlek ölçümü yoksa uyarı göster
  const handleReportDownload = (url: string) => {
    if (Object.keys(wheelSpeedResults).length === 0) {
      setPendingDownloadUrl(url)
      setShowReportWarning(true)
    } else {
      triggerDownload(url)
    }
  }

  const triggerDownload = (url: string) => {
    const a = document.createElement('a')
    a.href = url
    a.download = ''
    a.click()
  }

  const handleDownloadAnyway = () => {
    if (pendingDownloadUrl) triggerDownload(pendingDownloadUrl)
    setShowReportWarning(false)
    setPendingDownloadUrl(null)
  }

  return (
    <>
    {/* T21: Tekerlek ölçümü yapılmadan rapor indirme uyarı modal'ı */}
    {showReportWarning && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div className="bg-background rounded-lg border shadow-xl p-6 max-w-md w-full mx-4 space-y-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <h3 className="font-semibold text-base">Tekerlek doğrulaması yapılmadı</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Hiçbir araç için tekerlek-zemin temas noktası ölçümü yapılmadı. Raporda
                yalnızca homografi tabanlı ön tahminler (bbox) bulunacak — bu değerler
                sistematik olarak düşük olabilir (~%8, GPS doğrulamasında gözlemlendi).
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Birincil hız için her araç satırındaki <strong>"Hızı Ölç"</strong> butonunu
                kullanmanız önerilir. Raporu şimdi indirmek istiyorsanız devam edebilirsiniz.
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => { setShowReportWarning(false); setPendingDownloadUrl(null) }}>
              İptal
            </Button>
            <Button variant="default" onClick={handleDownloadAnyway}>
              Yine de İndir
            </Button>
          </div>
        </div>
      </div>
    )}
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
                        Hız (km/h)
                        <InfoHint text="Tekerlek ölçümü yapıldıysa birincil hız büyük/koyu gösterilir; ön tahmin (bbox) grileşir. Tekerlek yoksa ön tahmin gösterilir." />
                      </span>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <span className="flex items-center justify-end gap-1">
                        Güven Aralığı
                        <InfoHint text="±değer: tekerlek ölçümü varsa onun CI'ı, yoksa ön tahminin %95 CI yarı genişliği." />
                      </span>
                    </th>
                    <th className="px-3 py-2 font-medium">
                      <span className="flex items-center gap-1">
                        Güven
                        <InfoHint text="Tekerlek ölçümü varsa onun güven seviyesi; yoksa ön tahminin güven seviyesi. HIGH, MEDIUM veya LOW." />
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
                    <tr
                    key={e.track_id}
                    className={`border-b last:border-0 ${e.out_of_calibration_zone ? 'bg-red-950/20' : ''}`}
                  >
                      <td className="px-3 py-2 tabular-nums text-muted-foreground">#{e.track_id}</td>
                      <td className="px-3 py-2">
                        <span>{e.vehicle_class}</span>
                        {e.out_of_calibration_zone && (
                          <span
                            className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-bold bg-red-900/60 text-red-300 border border-red-700/60"
                            title={`Kalibrasyon dışı — hull-içi kare oranı: ${((e.hull_inside_fraction ?? 0) * 100).toFixed(0)}%. Homografi bu bölgede geçersiz olabilir; hız adli raporda GÜVEN İLMEZ olarak işaretlenir.`}
                          >
                            KAL. DIŞI
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {wheelSpeedResults[e.track_id] ? (
                          <div className="space-y-0.5">
                            <div className="text-base font-bold tabular-nums leading-none">
                              {wheelSpeedResults[e.track_id].value_kmh.toFixed(1)}
                              <span className="text-xs font-normal text-muted-foreground ml-0.5">km/h</span>
                            </div>
                            <div className="text-[10px] text-muted-foreground tabular-nums">
                              ön: {e.speed_kmh.toFixed(1)}
                              {!e.out_of_calibration_zone && (e.hull_inside_fraction ?? 1) < 0.8 && (
                                <span className="ml-0.5 text-amber-500" title="Bazı kareler kalibrasyon dışı">⚠</span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-0.5">
                            <div className="tabular-nums text-muted-foreground">
                              {e.speed_kmh.toFixed(1)}
                              {!e.out_of_calibration_zone && (e.hull_inside_fraction ?? 1) < 0.8 && (
                                <span className="ml-1 text-[9px] text-amber-500" title={`Hull-içi: ${((e.hull_inside_fraction ?? 0) * 100).toFixed(0)}%`}>⚠</span>
                              )}
                            </div>
                            <div className="text-[10px] text-amber-600 whitespace-nowrap">Tekerlek ölçümü önerilir</div>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                        ± {(wheelSpeedResults[e.track_id]?.ci_kmh ?? e.ci_kmh).toFixed(1)}
                      </td>
                      <td className="px-3 py-2">
                        <ConfidenceBadge level={wheelSpeedResults[e.track_id]?.confidence_level ?? e.confidence_level} />
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
                          variant={wheelTrackId === e.track_id ? 'default' : (wheelSpeedResults[e.track_id] ? 'secondary' : 'outline')}
                          size="sm"
                          onClick={() => {
                            setWheelTrackId(wheelTrackId === e.track_id ? null : e.track_id)
                            if (axleTrackId === e.track_id) setAxleTrackId(null)
                          }}
                        >
                          <Target className="size-3.5" />
                          {wheelSpeedResults[e.track_id] ? 'Güncelle' : 'Hızı Ölç'}
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
            onWheelSpeedResult={handleWheelSpeedResult}
            onWheelOverlayReady={(tid) => {
              setWheelOverlayTracks((prev) => new Set([...prev, tid]))
              setActiveOverlay(tid)
            }}
          />
        )}

        <MethodInfoCard />

        {/* Overlay video — T25: bbox / tekerlek toggle */}
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <h3 className="text-sm font-medium">Overlay Video</h3>
            <div className="flex flex-col items-end gap-1">
              {sourceJobId && (
                <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700 font-medium">
                  ⟳ Yeniden kalibrasyon uygulandı (kaynak: {sourceJobId})
                </span>
              )}
            </div>
          </div>

          {/* Toggle — birden fazla overlay varsa seçici göster */}
          {wheelOverlayTracks.size > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <button
                className={`rounded border px-3 py-1 text-xs font-medium transition-colors ${
                  activeOverlay === 'bbox'
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-card text-muted-foreground hover:bg-muted'
                }`}
                onClick={() => setActiveOverlay('bbox')}
              >
                Ön Tahmin (bbox)
              </button>
              {[...wheelOverlayTracks].map((tid) => (
                <button
                  key={tid}
                  className={`rounded border px-3 py-1 text-xs font-medium transition-colors ${
                    activeOverlay === tid
                      ? 'bg-emerald-600 text-white border-emerald-600'
                      : 'bg-card text-muted-foreground hover:bg-muted'
                  }`}
                  onClick={() => setActiveOverlay(tid)}
                >
                  Tekerlek #{tid}
                </button>
              ))}
            </div>
          )}

          <video
            key={activeOverlay === 'bbox' ? `bbox-${jobId}` : `wheel-${activeOverlay}-${jobId}`}
            controls
            src={
              activeOverlay === 'bbox'
                ? api.overlayUrl(jobId)
                : api.wheelOverlayUrl(jobId, activeOverlay as number)
            }
            className="w-full rounded-lg border bg-canvas"
          >
            Tarayıcınız video oynatmayı desteklemiyor.
          </video>
          <p className="text-xs text-muted-foreground">
            {activeOverlay === 'bbox'
              ? 'Ön tahmin: bbox hız değerleri. "Hızı Ölç" → "Bu Hızla Overlay Oluştur" ile tekerlek overlay\'ini oluşturun.'
              : `Tekerlek hızı overlay: Track #${activeOverlay} için operatör ölçüm değeri (* ile işaretli). Diğer araçlar bbox hızıyla gösterilir.`}
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
          <Button
            variant="outline"
            onClick={() => handleReportDownload(api.reportUrl(jobId))}
          >
            <FileText /> PDF Raporu İndir
          </Button>
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
    </>
  )
}
