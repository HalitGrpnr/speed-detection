import { useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, Check, Clock, Copy, FileVideo, Loader2, Ruler, UploadCloud } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { JobSummary, VideoMeta } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { useCrossRatio } from '@/features/crossratio/store'

const FPS_SOURCE_TR: Record<string, string> = {
  container: 'konteynerden',
  operator_override: 'operatör girişi',
}

function formatDuration(frames: number, fps: number): string {
  if (!fps) return '—'
  const total = Math.round(frames / fps)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function UploadStep() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const setVideoMeta = useWizard((s) => s.setVideoMeta)
  const setControlPoints = useWizard((s) => s.setControlPoints)
  const setCalibration = useWizard((s) => s.setCalibration)
  const setJobId = useWizard((s) => s.setJobId)
  const loadHistoricalJob = useWizard((s) => s.loadHistoricalJob)
  const setFlow = useWizard((s) => s.setFlow)
  const resetCrossRatio = useCrossRatio((s) => s.reset)

  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'new' | 'history'>('new')

  const mutation = useMutation({
    mutationFn: (file: File) => {
      setProgress(0)
      return api.uploadVideo(file, setProgress)
    },
    onSuccess: (meta: VideoMeta) => {
      // Yeni video → eski kalibrasyon/iş durumunu temizle
      setControlPoints([])
      setCalibration(null)
      setJobId(null)
      resetCrossRatio()
      setVideoMeta(meta)
    },
  })

  function handleFile(file: File | undefined | null) {
    if (!file) return
    setFileName(file.name)
    mutation.mutate(file)
  }

  const uploading = mutation.isPending

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 1 — Video Yükle</CardTitle>
        <CardDescription>
          Trafik kazası videosunu yükleyin. Bütünlük için SHA-256 hesaplanır; orijinal dosyaya
          asla yazılmaz, tüm işleme yereldir.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        {mutation.isError && (
          <StatusBanner tone="error">{(mutation.error as Error).message}</StatusBanner>
        )}

        {/* Video yüklenmişse sekme gösterme — direkt meta + StepFooter */}
        {videoMeta ? (
          <div className="space-y-4">
            <StatusBanner tone="success">
              Video yüklendi ve doğrulandı. Aşağıdaki bilgileri kontrol edip devam edin.
            </StatusBanner>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Meta label="Çözünürlük" value={`${videoMeta.width}×${videoMeta.height}`} />
              <Meta
                label="FPS"
                value={`${videoMeta.fps.toFixed(2)}`}
                hint={FPS_SOURCE_TR[videoMeta.fps_source] ?? videoMeta.fps_source}
              />
              <Meta label="Kare sayısı" value={videoMeta.frame_count.toLocaleString('tr-TR')} />
              <Meta label="Süre" value={formatDuration(videoMeta.frame_count, videoMeta.fps)} />
            </div>

            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                Dosya bütünlüğü doğrulandı · SHA-256
              </p>
              <ShaChip sha={videoMeta.sha256} />
            </div>

            <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
              <FileVideo /> Farklı video yükle
            </Button>

            <div className="space-y-2 border-t pt-4">
              <p className="text-sm font-medium">Ölçüm yöntemi</p>
              <button type="button" onClick={() => setFlow('crossratio')}
                className="group flex w-full items-start gap-3 rounded-xl border-2 border-primary/60 bg-primary/5 p-4 text-left transition-colors hover:bg-primary/10">
                <Ruler className="mt-0.5 size-5 shrink-0 text-primary" />
                <span className="flex-1">
                  <span className="flex items-center gap-2 font-semibold">
                    Tek araç, düz doğru boyunca hız
                    <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">önerilen</span>
                  </span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">
                    Kalibrasyon noktası gerekmez. Yoldaki şerit çizgileri (veya aracın kendi hareketi) ile bilinen bir uzunluk
                    (dingil mesafesi) kullanılır; sihirbaz her adımda ne yapacağınızı gösterir.
                  </span>
                </span>
                <ArrowRight className="mt-1 size-4 text-primary transition-transform group-hover:translate-x-0.5" />
              </button>
              <p className="text-xs text-muted-foreground">
                Alternatif: sahnede ölçülü kontrol noktalarıyla homografi kalibrasyonu — aşağıdaki “Devam” ile.
              </p>
            </div>
          </div>
        ) : uploading ? (
          <div className="space-y-3 rounded-xl border bg-muted/30 p-6">
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span className="font-medium">Yükleniyor…</span>
              <span className="truncate text-muted-foreground">{fileName}</span>
              <span className="ml-auto tabular-nums text-muted-foreground">{progress}%</span>
            </div>
            <Progress value={progress} />
          </div>
        ) : (
          <>
            {/* Sekme seçici */}
            <div className="flex overflow-hidden rounded-lg border text-sm font-medium">
              <button
                type="button"
                className={cn(
                  'flex-1 px-4 py-2.5 transition-colors',
                  activeTab === 'new'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-muted-foreground hover:bg-muted',
                )}
                onClick={() => setActiveTab('new')}
              >
                Yeni Analiz
              </button>
              <button
                type="button"
                className={cn(
                  'flex-1 border-l px-4 py-2.5 transition-colors flex items-center justify-center gap-2',
                  activeTab === 'history'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-muted-foreground hover:bg-muted',
                )}
                onClick={() => setActiveTab('history')}
              >
                <Clock className="size-3.5" /> Geçmiş Analizler
              </button>
            </div>

            {activeTab === 'new' && (
              <div
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOver(false)
                  handleFile(e.dataTransfer.files?.[0])
                }}
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 text-center transition-colors',
                  dragOver
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50 hover:bg-accent/40',
                )}
              >
                <UploadCloud className="size-10 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Tıklayın veya videoyu sürükleyip bırakın</p>
                  <p className="mt-1 text-xs text-muted-foreground">MP4, AVI, MKV, MOV · maksimum 10 GB</p>
                </div>
              </div>
            )}

            {activeTab === 'history' && (
              <HistoryPanelContent onLoad={loadHistoricalJob} />
            )}
          </>
        )}

        <StepFooter />
      </CardContent>
    </Card>
  )
}

function Meta({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-[0.7rem] text-muted-foreground">{hint}</p>}
    </div>
  )
}

function ShaChip({ sha }: { sha: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(sha)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        } catch {
          /* pano erişimi yoksa sessiz geç */
        }
      }}
      className="flex w-full items-center gap-2 rounded-md bg-muted px-3 py-2 text-left font-mono text-xs text-muted-foreground transition-colors hover:bg-muted/70"
      title="Kopyalamak için tıklayın"
    >
      <span className="break-all">{sha}</span>
      {copied ? (
        <Check className="ml-auto size-4 shrink-0 text-success" />
      ) : (
        <Copy className="ml-auto size-4 shrink-0" />
      )}
    </button>
  )
}

// ── T24 Geçmiş Analizler ─────────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('tr-TR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function HistoryPanelContent({
  onLoad,
}: {
  onLoad: (summary: JobSummary, controlPoints: import('@/lib/models').ControlPoint[]) => void
}) {
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const historyQuery = useQuery({
    queryKey: ['jobHistory'],
    queryFn: () => api.listJobs(),
    staleTime: 30_000,
  })

  const jobs = historyQuery.data ?? []

  async function handleLoad(summary: JobSummary) {
    setLoadingId(summary.job_id)
    setLoadError(null)
    try {
      const cal = await api.jobCalibration(summary.job_id)
      onLoad(summary, cal.control_points)
    } catch (err) {
      setLoadError((err as Error).message)
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div className="space-y-3">
      {loadError && <StatusBanner tone="error">{loadError}</StatusBanner>}

      {historyQuery.isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-3.5 animate-spin" /> Yükleniyor…
        </div>
      )}

      {historyQuery.isError && (
        <StatusBanner tone="error">{(historyQuery.error as Error).message}</StatusBanner>
      )}

      {historyQuery.isSuccess && jobs.length === 0 && (
        <p className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
          Henüz tamamlanmış analiz yok. Yeni bir analiz yaptığınızda burada görünür.
        </p>
      )}

      {jobs.length > 0 && (
        <div className="space-y-1.5">
          {jobs.map((job) => (
            <div
              key={job.job_id}
              className="flex items-center gap-3 rounded-md border bg-card px-3 py-2.5"
            >
              <FileVideo className="size-4 shrink-0 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  {job.video_filename ?? 'Bilinmeyen video'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(job.created_at)}
                  {' · '}
                  {job.vehicle_count} araç
                  {job.frame_count != null && job.fps != null && (
                    <> · {Math.round(job.frame_count / job.fps)}s</>
                  )}
                  {job.model_name && <> · {job.model_name}</>}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0 h-7 px-3 text-xs"
                disabled={loadingId === job.job_id}
                onClick={() => handleLoad(job)}
              >
                {loadingId === job.job_id ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : null}
                Yükle
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
