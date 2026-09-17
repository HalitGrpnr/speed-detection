import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download, FileText, Loader2, Map, RotateCcw, Ruler, Target } from 'lucide-react'
import { api } from '@/lib/api'
import type { SpeedEstimate, WheelSpeedResponse } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { cn } from '@/lib/utils'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { MethodInfoCard } from '@/components/common/MethodInfoCard'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { AxleCheckPanel } from './AxleCheckPanel'
import { SessionLogPanel } from './SessionLogPanel'
import { WheelSpeedPanel } from './WheelSpeedPanel'

type ActivePanel = 'axle' | 'wheel'

interface VehicleCardProps {
  estimate: SpeedEstimate
  wheelResult: WheelSpeedResponse | undefined
  isSelected: boolean
  activePanelType: ActivePanel | null
  onSelectAxle: () => void
  onSelectWheel: () => void
}

function VehicleCard({
  estimate: e,
  wheelResult,
  isSelected,
  activePanelType,
  onSelectAxle,
  onSelectWheel,
}: VehicleCardProps) {
  const hasWheel = !!wheelResult
  return (
    <div
      className={cn(
        'rounded-lg border p-4 space-y-3 transition-colors',
        isSelected ? 'border-primary bg-primary/5' : 'bg-card hover:border-primary/40',
        e.out_of_calibration_zone ? 'border-red-700/40 bg-red-950/10' : '',
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-mono text-muted-foreground">#{e.track_id}</span>
        <span className="text-sm font-medium">{e.vehicle_class}</span>
        <span className="text-xs text-muted-foreground">{e.frame_count} kare</span>
        {e.out_of_calibration_zone && (
          <span
            className="rounded px-1.5 py-0.5 text-[10px] font-bold bg-red-900/60 text-red-300 border border-red-700/60"
            title={`Kalibrasyon dışı — hull-içi: ${((e.hull_inside_fraction ?? 0) * 100).toFixed(0)}%`}
          >
            KAL. DIŞI
          </span>
        )}
        {!e.out_of_calibration_zone && (e.hull_inside_fraction ?? 1) < 0.8 && (
          <span
            className="text-xs text-amber-500"
            title={`Hull-içi kare oranı: ${((e.hull_inside_fraction ?? 0) * 100).toFixed(0)}%`}
          >
            ⚠ kısmi
          </span>
        )}
        <div className="ml-auto">
          <ConfidenceBadge
            level={hasWheel ? wheelResult.confidence_level : e.confidence_level}
          />
        </div>
      </div>

      {/* Hız kutuları */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md bg-muted/40 px-3 py-2.5">
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Ön Tahmin</p>
          <p className={cn('tabular-nums', hasWheel ? 'text-sm text-muted-foreground' : 'text-xl font-bold')}>
            {e.speed_kmh.toFixed(1)}
            <span className="text-xs font-normal ml-0.5">km/h</span>
          </p>
          <p className="text-[10px] text-muted-foreground mt-0.5">±{e.ci_kmh.toFixed(1)}</p>
        </div>

        {hasWheel ? (
          <div className="rounded-md bg-success/10 border border-success/30 px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-success mb-1">Birincil Hız ✓</p>
            <p className="text-xl font-bold tabular-nums">
              {wheelResult.value_kmh.toFixed(1)}
              <span className="text-xs font-normal ml-0.5">km/h</span>
            </p>
            <p className="text-[10px] text-muted-foreground mt-0.5">±{wheelResult.ci_kmh.toFixed(1)}</p>
          </div>
        ) : (
          <div className="rounded-md bg-warning/10 border border-warning/20 px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-warning mb-1">Birincil Hız</p>
            <p className="text-sm text-muted-foreground">Ölçüm önerilir</p>
          </div>
        )}
      </div>

      {/* Aksiyon butonları */}
      <div className="flex gap-2">
        <Button
          variant={isSelected && activePanelType === 'axle' ? 'default' : 'outline'}
          size="sm"
          className="flex-1 text-xs"
          onClick={onSelectAxle}
        >
          <Ruler className="size-3.5" /> Aks Doğrula
        </Button>
        <Button
          variant={
            isSelected && activePanelType === 'wheel'
              ? 'default'
              : hasWheel
                ? 'secondary'
                : 'outline'
          }
          size="sm"
          className="flex-1 text-xs"
          onClick={onSelectWheel}
        >
          <Target className="size-3.5" />
          {hasWheel ? 'Güncelle' : 'Hızı Ölç'}
        </Button>
      </div>
    </div>
  )
}

export function ResultsStep() {
  const jobId = useWizard((s) => s.jobId)
  const sourceJobId = useWizard((s) => s.sourceJobId)
  const videoMeta = useWizard((s) => s.videoMeta)
  const controlPoints = useWizard((s) => s.controlPoints)
  const reset = useWizard((s) => s.reset)

  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null)
  const [activePanelType, setActivePanelType] = useState<ActivePanel | null>(null)
  const [showPlanView, setShowPlanView] = useState(false)
  const [hasV2Report, setHasV2Report] = useState(false)
  const [wheelSpeedResults, setWheelSpeedResults] = useState<Record<number, WheelSpeedResponse>>({})
  const [showReportWarning, setShowReportWarning] = useState(false)
  const [pendingDownloadUrl, setPendingDownloadUrl] = useState<string | null>(null)
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

  const handleWheelSpeedResult = (trackId: number, res: WheelSpeedResponse) =>
    setWheelSpeedResults((prev) => ({ ...prev, [trackId]: res }))

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

  const selectPanel = (trackId: number, panel: ActivePanel) => {
    if (selectedTrackId === trackId && activePanelType === panel) {
      setActivePanelType(null)
    } else {
      setSelectedTrackId(trackId)
      setActivePanelType(panel)
    }
  }

  return (
    <>
      {/* Rapor indirme uyarı modalı */}
      {showReportWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card rounded-lg border shadow-pop p-6 max-w-md w-full mx-4 space-y-4">
            <div className="flex items-start gap-3">
              <AlertTriangle
                className="size-5 mt-0.5 shrink-0"
                style={{ color: 'hsl(var(--warning))' }}
              />
              <div>
                <h3 className="font-semibold text-base">Tekerlek doğrulaması yapılmadı</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Hiçbir araç için tekerlek-zemin temas noktası ölçümü yapılmadı. Raporda
                  yalnızca homografi tabanlı ön tahminler (bbox) bulunacak — bu değerler
                  sistematik olarak düşük olabilir (~%8, GPS doğrulamasında gözlemlendi).
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Birincil hız için araç kartlarındaki{' '}
                  <strong>"Hızı Ölç"</strong> butonunu kullanın.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowReportWarning(false)
                  setPendingDownloadUrl(null)
                }}
              >
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
            {result.vehicle_count} araç tespit edildi. Birincil hızı ölçmek için bir araç
            kartındaki <strong>"Hızı Ölç"</strong> butonunu kullanın.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {sourceJobId && (
            <StatusBanner tone="info">
              Bu analiz aks doğrulaması eklenerek yeniden hesaplandı — tespit tekrarlanmadı.
              Orijinal:{' '}
              <code className="font-mono text-xs">{sourceJobId.slice(0, 8)}…</code>
            </StatusBanner>
          )}

          {result.estimates.length === 0 ? (
            <StatusBanner tone="warning">
              Hız tahmini üretilemedi (yeterli/uzun takip bulunamadı). Overlay videoyu inceleyin
              veya kare adımını düşürüp tekrar deneyin.
            </StatusBanner>
          ) : (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
              {/* Sol: Araç kart listesi */}
              <div className="space-y-3">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Tespit Edilen Araçlar
                </p>
                {result.estimates.map((e) => (
                  <VehicleCard
                    key={e.track_id}
                    estimate={e}
                    wheelResult={wheelSpeedResults[e.track_id]}
                    isSelected={selectedTrackId === e.track_id}
                    activePanelType={selectedTrackId === e.track_id ? activePanelType : null}
                    onSelectAxle={() => selectPanel(e.track_id, 'axle')}
                    onSelectWheel={() => selectPanel(e.track_id, 'wheel')}
                  />
                ))}
              </div>

              {/* Sağ: Video + aktif panel */}
              <div className="space-y-3">
                {/* Overlay sekme seçici */}
                <div className="flex overflow-hidden rounded-md border text-xs font-medium">
                  <button
                    className={cn(
                      'flex-1 px-3 py-2 transition-colors',
                      activeOverlay === 'bbox'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-card text-muted-foreground hover:bg-muted',
                    )}
                    onClick={() => setActiveOverlay('bbox')}
                  >
                    Ön Tahmin (bbox)
                  </button>
                  {[...wheelOverlayTracks].map((tid) => (
                    <button
                      key={tid}
                      className={cn(
                        'flex-1 border-l px-3 py-2 transition-colors',
                        activeOverlay === tid
                          ? 'bg-success text-success-foreground'
                          : 'bg-card text-muted-foreground hover:bg-muted',
                      )}
                      onClick={() => setActiveOverlay(tid)}
                    >
                      Tekerlek #{tid}
                    </button>
                  ))}
                </div>

                <video
                  key={
                    activeOverlay === 'bbox'
                      ? `bbox-${jobId}`
                      : `wheel-${activeOverlay}-${jobId}`
                  }
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

                {wheelOverlayTracks.size === 0 && (
                  <p className="text-xs text-muted-foreground">
                    "Hızı Ölç" → "Bu Hızla Overlay Oluştur" ile tekerlek overlay'i ekleyin.
                  </p>
                )}

                {selectedTrackId != null &&
                  activePanelType === 'axle' &&
                  jobId &&
                  videoMeta && (
                    <AxleCheckPanel
                      jobId={jobId}
                      videoId={videoMeta.video_id}
                      trackId={selectedTrackId}
                      controlPoints={controlPoints}
                      onClose={() => setActivePanelType(null)}
                      onReportRegenerated={() => setHasV2Report(true)}
                    />
                  )}

                {selectedTrackId != null &&
                  activePanelType === 'wheel' &&
                  jobId &&
                  videoMeta && (
                    <WheelSpeedPanel
                      jobId={jobId}
                      videoId={videoMeta.video_id}
                      trackId={selectedTrackId}
                      frameCount={videoMeta.frame_count}
                      onClose={() => setActivePanelType(null)}
                      onReportRegenerated={() => setHasV2Report(true)}
                      onWheelSpeedResult={handleWheelSpeedResult}
                      onWheelOverlayReady={(tid) => {
                        setWheelOverlayTracks((prev) => new Set([...prev, tid]))
                        setActiveOverlay(tid)
                      }}
                    />
                  )}

                {selectedTrackId == null && (
                  <div className="rounded-lg border border-dashed bg-muted/20 px-4 py-8 text-center text-sm text-muted-foreground">
                    Bir araç kartından{' '}
                    <strong>"Hızı Ölç"</strong> veya <strong>"Aks Doğrula"</strong> ile
                    ölçüm başlatın.
                  </div>
                )}
              </div>
            </div>
          )}

          <MethodInfoCard />

          {/* Kuş bakışı */}
          <div className="space-y-2">
            <Button variant="outline" size="sm" onClick={() => setShowPlanView((v) => !v)}>
              <Map className="size-3.5" />
              {showPlanView ? 'Kuş Bakışını Gizle' : 'Kuş Bakışını Göster'}
            </Button>
            {showPlanView && (
              <img
                src={api.jobPlanViewUrl(jobId)}
                alt="Kuş bakışı (plan view)"
                className="w-full rounded-lg border bg-canvas"
              />
            )}
          </div>

          {/* İndirmeler */}
          <div className="flex flex-wrap items-center gap-3">
            {hasV2Report ? (
              <>
                <a
                  href={api.reportV2Url(jobId)}
                  download
                  className={buttonVariants({ variant: 'default' })}
                >
                  <FileText /> PDF İndir (Tekerlek Doğrulamalı)
                </a>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleReportDownload(api.reportUrl(jobId!))}
                >
                  <FileText /> Ön Tahmin Raporu
                </Button>
              </>
            ) : (
              <Button variant="default" onClick={() => handleReportDownload(api.reportUrl(jobId!))}>
                <FileText /> PDF Raporu İndir
              </Button>
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
