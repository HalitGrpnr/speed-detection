import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Plus, Trash2, Loader2, Crosshair, ChevronRight } from 'lucide-react'
import { api } from '@/lib/api'
import type { AxleTimingCrossing, AxleTimingResponse } from '@/lib/models'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBanner } from '@/components/common/StatusBanner'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { CalibrationCanvas } from '@/features/calibration/CalibrationCanvas'
import type { ControlPoint } from '@/lib/models'

interface Props {
  jobId: string
  videoId: string
  trackId: number
  frameCount: number
  onClose: () => void
}

type Step =
  | 'target'         // referans noktası seç
  | 'front_before'   // ön teker N karesi
  | 'front_after'    // ön teker N+1 karesi
  | 'rear_before'    // arka teker M karesi
  | 'rear_after'     // arka teker M+1 karesi

interface DraftCrossing {
  target_px?: [number, number]
  front_frame_n?: number
  front_pixel_n?: [number, number]
  front_frame_n1?: number
  front_pixel_n1?: [number, number]
  rear_frame_n?: number
  rear_pixel_n?: [number, number]
  rear_frame_n1?: number
  rear_pixel_n1?: [number, number]
}

const STEP_ORDER: Step[] = ['target', 'front_before', 'front_after', 'rear_before', 'rear_after']

const STEP_LABELS: Record<Step, string> = {
  target: '1. Referans noktasını seç — yol üzerindeki sabit bir özelliği (çizgi, kenar) tıkla',
  front_before: '2. Ön tekerlek — referans çizgisinden ÖNCE kare (N)',
  front_after: '3. Ön tekerlek — referans çizgisinden SONRA kare (N+1)',
  rear_before: '4. Arka tekerlek — referans çizgisinden ÖNCE kare (M)',
  rear_after: '5. Arka tekerlek — referans çizgisinden SONRA kare (M+1)',
}

function stepToFrameKey(step: Step): keyof DraftCrossing | null {
  const map: Partial<Record<Step, keyof DraftCrossing>> = {
    front_before: 'front_frame_n',
    front_after: 'front_frame_n1',
    rear_before: 'rear_frame_n',
    rear_after: 'rear_frame_n1',
  }
  return map[step] ?? null
}

function stepToPixelKey(step: Step): keyof DraftCrossing | null {
  const map: Partial<Record<Step, keyof DraftCrossing>> = {
    front_before: 'front_pixel_n',
    front_after: 'front_pixel_n1',
    rear_before: 'rear_pixel_n',
    rear_after: 'rear_pixel_n1',
  }
  return map[step] ?? null
}

export function AxleTimingPanel({ jobId, videoId, trackId, frameCount, onClose }: Props) {
  const [wheelbaseM, setWheelbaseM] = useState('2.65')
  const [crossings, setCrossings] = useState<AxleTimingCrossing[]>([])
  const [draft, setDraft] = useState<DraftCrossing | null>(null)
  const [currentStep, setCurrentStep] = useState<Step>('target')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [frameInput, setFrameInput] = useState('')
  const [result, setResult] = useState<AxleTimingResponse | null>(null)

  const calcMutation = useMutation({
    mutationFn: () =>
      api.axleTiming(jobId, trackId, {
        crossings,
        wheelbase_m: parseFloat(wheelbaseM) || 2.65,
      }),
    onSuccess: setResult,
  })

  const isAddingCrossing = draft !== null

  const startNewCrossing = () => {
    setDraft({})
    setCurrentStep('target')
    setCurrentFrame(0)
    setFrameInput('')
  }

  const cancelDraft = () => {
    setDraft(null)
  }

  const canvasPoints = (step: Step, d: DraftCrossing): ControlPoint[] => {
    const points: ControlPoint[] = []
    if (d.target_px) {
      points.push({ id: 'target', pixel: d.target_px, world_m: [0, 0], source: 'operator', held_out: false })
    }
    const pk = stepToPixelKey(step)
    if (pk && d[pk]) {
      points.push({ id: 'current', pixel: d[pk] as [number, number], world_m: [0, 0], source: 'operator', held_out: false })
    }
    return points
  }

  const handleCanvasClick = (pixel: [number, number]) => {
    if (!draft) return

    if (currentStep === 'target') {
      setDraft((prev) => ({ ...prev, target_px: pixel }))
    } else {
      const pk = stepToPixelKey(currentStep)
      const fk = stepToFrameKey(currentStep)
      if (pk && fk) {
        setDraft((prev) => ({ ...prev, [pk]: pixel, [fk]: currentFrame }))
      }
    }
  }

  const canAdvance = (step: Step, d: DraftCrossing): boolean => {
    if (step === 'target') return !!d.target_px
    const pk = stepToPixelKey(step)
    const fk = stepToFrameKey(step)
    return !!(pk && fk && d[pk] && d[fk] !== undefined)
  }

  const advance = () => {
    if (!draft) return
    const idx = STEP_ORDER.indexOf(currentStep)
    if (idx < STEP_ORDER.length - 1) {
      const nextStep = STEP_ORDER[idx + 1]
      setCurrentStep(nextStep)
      // Sonraki kare için N+1 default'u
      if (nextStep === 'front_after' && draft.front_frame_n !== undefined) {
        setCurrentFrame(draft.front_frame_n + 1)
        setFrameInput(String(draft.front_frame_n + 1))
      } else if (nextStep === 'rear_after' && draft.rear_frame_n !== undefined) {
        setCurrentFrame(draft.rear_frame_n + 1)
        setFrameInput(String(draft.rear_frame_n + 1))
      }
    } else {
      // Tüm adımlar tamam — crossing'e ekle
      const c: AxleTimingCrossing = {
        target_px: draft.target_px!,
        front_frame_n: draft.front_frame_n!,
        front_pixel_n: draft.front_pixel_n!,
        front_frame_n1: draft.front_frame_n1!,
        front_pixel_n1: draft.front_pixel_n1!,
        rear_frame_n: draft.rear_frame_n!,
        rear_pixel_n: draft.rear_pixel_n!,
        rear_frame_n1: draft.rear_frame_n1!,
        rear_pixel_n1: draft.rear_pixel_n1!,
      }
      setCrossings((prev) => [...prev, c])
      setDraft(null)
      setResult(null)
      calcMutation.reset()
    }
  }

  const removeCrossing = (i: number) => {
    setCrossings((prev) => prev.filter((_, j) => j !== i))
    setResult(null)
    calcMutation.reset()
  }

  const goToFrame = (n: number) => {
    const clamped = Math.max(0, Math.min(frameCount - 1, n))
    setCurrentFrame(clamped)
  }

  const frameForStep = (step: Step): number | undefined => {
    if (step === 'target') return currentFrame
    return currentFrame
  }

  const displayFrame = frameForStep(currentStep) ?? currentFrame
  const imageUrl = api.frameUrl(videoId, displayFrame)

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      {/* Başlık */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Crosshair className="size-4 text-muted-foreground" />
          Dingil Adımlama — Takip #{trackId}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>Kapat</Button>
      </div>

      {/* Bilgi banner */}
      <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm text-blue-800 space-y-1">
        <p className="font-medium">H-bağımsız hız ölçümü</p>
        <p className="text-xs text-blue-700">
          Sahnedeki görünür bir yol referansını (çizgi, kenar) işaret olarak kullan.
          Ön ve arka tekerleğin bu referansı geçtiği anı bracketing ile belirle.
          Hız = dingil mesafesi ÷ Δt — kalibrasyon kalitesinden bağımsız.
        </p>
      </div>

      {/* Dingil mesafesi */}
      <div className="flex items-center gap-2 text-sm">
        <label className="text-muted-foreground whitespace-nowrap">Dingil mesafesi (m):</label>
        <Input
          type="number" step="0.01" min="0.5" max="10"
          value={wheelbaseM}
          onChange={(e) => setWheelbaseM(e.target.value)}
          className="h-7 w-24 text-sm"
        />
        <span className="text-xs text-muted-foreground">(sedan ≈ 2.65, SUV ≈ 2.8)</span>
      </div>

      {/* Crossing listesi */}
      {crossings.length > 0 && !isAddingCrossing && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">Geçiş olayları ({crossings.length}):</p>
          {crossings.map((c, i) => (
            <div key={i} className="flex items-center gap-2 rounded border bg-card px-3 py-1.5 text-xs">
              <span className="font-medium text-muted-foreground">#{i + 1}</span>
              <span className="tabular-nums">
                Ön K{c.front_frame_n}–{c.front_frame_n1}
              </span>
              <ChevronRight className="size-3 text-muted-foreground" />
              <span className="tabular-nums">
                Arka K{c.rear_frame_n}–{c.rear_frame_n1}
              </span>
              <span className="text-muted-foreground ml-1">
                ref=({c.target_px[0].toFixed(0)}, {c.target_px[1].toFixed(0)})
              </span>
              <button className="ml-auto text-muted-foreground hover:text-destructive"
                onClick={() => removeCrossing(i)}>
                <Trash2 className="size-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Crossing ekleme wizard */}
      {isAddingCrossing && draft ? (
        <div className="space-y-3 rounded-md border border-primary/30 bg-primary/5 p-3">
          <p className="text-xs font-medium text-primary">{STEP_LABELS[currentStep]}</p>

          {/* Kare navigasyonu (target adımında da gerekli — referans noktası herhangi bir karede) */}
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Kare: <span className="font-semibold tabular-nums text-foreground">{currentFrame}</span></span>
            <Button variant="outline" size="sm" className="h-7 px-2" onClick={() => goToFrame(currentFrame - 1)}>← Önceki</Button>
            <Button variant="outline" size="sm" className="h-7 px-2" onClick={() => goToFrame(currentFrame + 1)}>Sonraki →</Button>
            <Input type="number" placeholder="kare no" value={frameInput}
              onChange={(e) => setFrameInput(e.target.value)} className="h-7 w-24" />
            <Button variant="secondary" size="sm" className="h-7 px-2" disabled={frameInput === ''}
              onClick={() => { const n = Number(frameInput); if (Number.isFinite(n)) goToFrame(n) }}>
              Git
            </Button>
          </div>

          <CalibrationCanvas
            imageUrl={imageUrl}
            points={canvasPoints(currentStep, draft)}
            selectedId={null}
            onAdd={handleCanvasClick}
            onMove={(_id, pixel) => handleCanvasClick(pixel)}
            onSelect={() => {}}
          />

          <div className="flex gap-2">
            <Button size="sm"
              disabled={!canAdvance(currentStep, draft)}
              onClick={advance}>
              {currentStep === 'rear_after' ? 'Geçiş Ekle' : 'Sonraki Adım →'}
            </Button>
            <Button variant="ghost" size="sm" onClick={cancelDraft}>İptal</Button>
          </div>

          {/* İlerleme göstergesi */}
          <div className="flex gap-1">
            {STEP_ORDER.map((s) => (
              <div key={s} className={`h-1 flex-1 rounded-full ${s === currentStep ? 'bg-primary' : STEP_ORDER.indexOf(s) < STEP_ORDER.indexOf(currentStep) ? 'bg-primary/40' : 'bg-muted'}`} />
            ))}
          </div>
        </div>
      ) : (
        <Button variant="outline" size="sm" onClick={startNewCrossing}>
          <Plus className="size-3.5 mr-1" />
          Geçiş Ekle
        </Button>
      )}

      {/* Hesapla */}
      {crossings.length > 0 && !isAddingCrossing && !result && (
        <Button
          disabled={calcMutation.isPending || crossings.length === 0}
          onClick={() => calcMutation.mutate()}
        >
          {calcMutation.isPending ? <Loader2 className="animate-spin" /> : <Crosshair />}
          Hızı Hesapla
        </Button>
      )}

      {calcMutation.isError && (
        <StatusBanner tone="error">{(calcMutation.error as Error).message}</StatusBanner>
      )}

      {/* Sonuç */}
      {result && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-4 flex-wrap">
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Dingil Adımlama Hızı</div>
              <div className="text-3xl font-bold tabular-nums leading-none">
                {result.speed_kmh.toFixed(1)}
                <span className="text-base font-normal text-muted-foreground ml-1">km/h</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">CI</div>
              <div className="text-lg font-semibold tabular-nums">± {result.ci_kmh.toFixed(1)} km/h</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Güven</div>
              <ConfidenceBadge level={result.confidence_level} />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Geçiş sayısı</div>
              <div className="font-semibold tabular-nums">{result.crossing_count}</div>
            </div>
          </div>

          {result.crossing_count > 1 && (
            <div>
              <div className="text-xs text-muted-foreground mb-1">Geçiş hızları (audit):</div>
              <div className="flex flex-wrap gap-2">
                {result.crossing_speeds_kmh.map((v, i) => (
                  <span key={i} className="rounded border bg-muted/40 px-2 py-0.5 text-xs tabular-nums font-medium">
                    #{i + 1}: {v.toFixed(1)} km/h
                    <span className="text-muted-foreground ml-1">Δt={result.delta_t_per_crossing_s[i].toFixed(3)}s</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="text-xs text-muted-foreground">
            Dingil mesafesi: <span className="font-medium">{wheelbaseM} m</span>
            {' · '}Yöntem: H-bağımsız, salt zamanlama
          </div>

          {result.warnings.length > 0 && (
            <StatusBanner tone="warning">{result.warnings.join(' ')}</StatusBanner>
          )}

          <Button variant="outline" size="sm" onClick={() => { setResult(null); calcMutation.reset() }}>
            Yeniden Hesapla
          </Button>
        </div>
      )}
    </div>
  )
}
