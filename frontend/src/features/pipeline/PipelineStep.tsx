import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronDown, Loader2, Play, RotateCcw } from 'lucide-react'
import { api } from '@/lib/api'
import type { ModelSize } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'

function formatEta(s: number | null | undefined): string {
  if (s == null) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return m > 0 ? `${m} dk ${sec} sn` : `${sec} sn`
}

export function PipelineStep() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const cal = useWizard((s) => s.calibration)
  const points = useWizard((s) => s.controlPoints)
  const selectedFrame = useWizard((s) => s.selectedFrame)
  const jobId = useWizard((s) => s.jobId)
  const setJobId = useWizard((s) => s.setJobId)
  const goTo = useWizard((s) => s.goTo)

  const [modelSize, setModelSize] = useState<ModelSize>('medium')
  const [frameStep, setFrameStep] = useState(1)
  const [fpsEnabled, setFpsEnabled] = useState(false)
  const [fpsValue, setFpsValue] = useState(25)

  const start = useMutation({
    mutationFn: () =>
      api.startPipeline({
        video_id: videoMeta!.video_id,
        calibration: cal!,
        control_points: points,
        frame_step: frameStep,
        model_size: modelSize,
        fps_override: fpsEnabled ? fpsValue : null,
        frame_n: selectedFrame,
      }),
    onSuccess: (r) => setJobId(r.job_id),
  })

  const statusQuery = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => api.jobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const st = q.state.data?.state
      return st === 'done' || st === 'error' ? false : 1500
    },
  })

  const status = statusQuery.data
  const doneState = status?.state === 'done'
  const errorState = status?.state === 'error' || statusQuery.isError
  const active = !!jobId && !doneState && !errorState

  const [advancedOpen, setAdvancedOpen] = useState(false)

  // Tamamlanınca sonuç adımına geç.
  useEffect(() => {
    if (doneState) goTo(6)
  }, [doneState, goTo])

  if (!videoMeta || !cal) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Adım 5 — Analiz</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <StatusBanner tone="warning">Önce kalibrasyonu tamamlayın (Adım 3–4).</StatusBanner>
          <StepFooter />
        </CardContent>
      </Card>
    )
  }

  const locked = active || start.isPending
  const reset = () => {
    setJobId(null)
    start.reset()
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 5 — Analizi Başlat</CardTitle>
        <CardDescription>
          Tespit + takip + hız hesabı arka planda çalışır. Varsayılan ayarlar adli doğruluk
          önceliklidir.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Gelişmiş ayarlar accordion */}
        <div className="rounded-lg border">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/30 transition-colors"
            onClick={() => setAdvancedOpen((v) => !v)}
            disabled={locked}
          >
            <span>Gelişmiş Ayarlar</span>
            <div className="flex items-center gap-2">
              {locked ? (
                <span className="text-xs text-muted-foreground tabular-nums">
                  {modelSize} · Kare adımı {frameStep}
                  {fpsEnabled ? ` · FPS: ${fpsValue}` : ''}
                </span>
              ) : (
                <span className="text-xs text-muted-foreground">
                  Model: {modelSize}
                </span>
              )}
              <ChevronDown
                className={`size-4 text-muted-foreground transition-transform ${advancedOpen && !locked ? 'rotate-180' : ''}`}
              />
            </div>
          </button>

          {advancedOpen && !locked && (
            <div className="border-t px-4 py-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <label className="space-y-1 text-sm">
                  <span className="font-medium">Model Boyutu</span>
                  <select
                    value={modelSize}
                    onChange={(e) => setModelSize(e.target.value as ModelSize)}
                    className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="nano">Nano (CPU, hızlı)</option>
                    <option value="small">Small (daha iyi tespit)</option>
                    <option value="medium">Medium (en iyi, yavaş)</option>
                  </select>
                  {modelSize !== 'medium' && (
                    <span className="text-[10px] text-warning">Adli doğruluk için Medium önerilir</span>
                  )}
                </label>

                <label className="space-y-1 text-sm">
                  <span className="font-medium">Kare Adımı</span>
                  <select
                    value={frameStep}
                    onChange={(e) => setFrameStep(Number(e.target.value))}
                    className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value={1}>1 (her kare)</option>
                    <option value={2}>2 (her 2. kare)</option>
                    <option value={3}>3 (her 3. kare)</option>
                    <option value={5}>5 (düşük RAM)</option>
                  </select>
                </label>

                <label className="space-y-1 text-sm">
                  <span className="font-medium">FPS Geçersiz Kıl</span>
                  <div className="flex h-9 items-center gap-2">
                    <input
                      type="checkbox"
                      checked={fpsEnabled}
                      onChange={(e) => setFpsEnabled(e.target.checked)}
                      className="size-4 accent-primary"
                    />
                    <Input
                      type="number"
                      step="0.01"
                      min="1"
                      value={fpsValue}
                      disabled={!fpsEnabled}
                      onChange={(e) => setFpsValue(Number(e.target.value))}
                      className="h-9"
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">VFR video için manuel girin.</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Durum */}
        {active && (
          <div className="space-y-2 rounded-lg border bg-muted/30 p-4">
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span className="font-medium">
                {status?.state === 'queued' ? 'Sıraya alındı…' : 'Analiz çalışıyor…'}
              </span>
              <span className="ml-auto tabular-nums text-muted-foreground">
                {Math.round(status?.progress_pct ?? 0)}%
                {status?.eta_s != null && ` · ~${formatEta(status.eta_s)}`}
              </span>
            </div>
            <Progress value={status?.progress_pct ?? 0} />
          </div>
        )}

        {errorState && (
          <div className="space-y-2">
            <StatusBanner tone="error">
              {status?.error ?? (start.error as Error)?.message ?? 'Analiz başarısız oldu.'}
            </StatusBanner>
            <Button variant="outline" size="sm" onClick={reset}>
              <RotateCcw /> Tekrar dene
            </Button>
          </div>
        )}

        {doneState && (
          <StatusBanner tone="success">Analiz tamamlandı. Sonuçlara yönlendiriliyorsunuz…</StatusBanner>
        )}

        {!jobId && !start.isPending && (
          <Button variant="success" onClick={() => start.mutate()}>
            <Play /> Analizi Başlat
          </Button>
        )}
        {start.isPending && (
          <Button variant="success" disabled>
            <Loader2 className="animate-spin" /> Başlatılıyor…
          </Button>
        )}

        <StepFooter />
      </CardContent>
    </Card>
  )
}
