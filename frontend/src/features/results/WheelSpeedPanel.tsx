import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FileText, Loader2, Target, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { ControlPoint, WheelSpeedResponse } from '@/lib/models'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBanner } from '@/components/common/StatusBanner'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { CalibrationCanvas } from '@/features/calibration/CalibrationCanvas'

interface Props {
  jobId: string
  videoId: string
  trackId: number
  frameCount: number
  onClose: () => void
  onReportRegenerated?: () => void
}

/**
 * T16 — Operatör-tekerlek hız ölçümü.
 * Operatör 2-5 farklı karede aynı tekerin yere değdiği noktayı işaretler;
 * backend H + fps ile birincil hızı hesaplar (bbox parallax'ından bağımsız).
 */
export function WheelSpeedPanel({
  jobId, videoId, trackId, frameCount, onClose, onReportRegenerated,
}: Props) {
  // frame → pixel eşlemesi (her kare en fazla 1 işaret)
  const [marks, setMarks] = useState<Record<number, [number, number]>>({})
  const [currentFrame, setCurrentFrame] = useState(0)
  const [frameInput, setFrameInput] = useState('')
  const [result, setResult] = useState<WheelSpeedResponse | null>(null)

  const markEntries = Object.entries(marks)
    .map(([f, p]) => ({ frame: Number(f), pixel: p }))
    .sort((a, b) => a.frame - b.frame)

  const currentPixel = marks[currentFrame]
  const canvasPoints: ControlPoint[] = currentPixel
    ? [{ id: 'wheel_mark', pixel: currentPixel, world_m: [0, 0], source: 'operator', held_out: false }]
    : []

  const goToFrame = (n: number) => {
    const clamped = Math.max(0, Math.min(frameCount - 1, n))
    setCurrentFrame(clamped)
  }

  const handleAdd = (pixel: [number, number]) => {
    setMarks((prev) => ({ ...prev, [currentFrame]: pixel }))
  }

  const handleMove = (_id: string, pixel: [number, number]) => {
    setMarks((prev) => ({ ...prev, [currentFrame]: pixel }))
  }

  const removeMark = (frame: number) => {
    setMarks((prev) => {
      const next = { ...prev }
      delete next[frame]
      return next
    })
  }

  const calcMutation = useMutation({
    mutationFn: () =>
      api.wheelSpeed(jobId, trackId, {
        marks: markEntries.map((m) => ({ frame: m.frame, pixel: m.pixel })),
      }),
    onSuccess: (data) => setResult(data),
  })

  const regenerateMutation = useMutation({
    mutationFn: () => api.regenerateReport(jobId),
    onSuccess: () => onReportRegenerated?.(),
  })

  const handleReset = () => {
    setMarks({})
    setResult(null)
    calcMutation.reset()
    regenerateMutation.reset()
  }

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      {/* Başlık */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Target className="size-4 text-muted-foreground" />
          Hızı Ölç — Takip #{trackId}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>Kapat</Button>
      </div>

      {/* Yönlendirme */}
      <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm text-blue-800 space-y-1">
        <p className="font-medium">Nasıl yapılır? (3 adım)</p>
        <ol className="list-decimal list-inside text-xs space-y-0.5 text-blue-700">
          <li>Videoda aracın bir tekerin yere değdiği yere tıkla.</li>
          <li>İleri/geri ile farklı bir kareye geç — AYNI tekeri tekrar tıkla. En az 2, tercihen 3-5 kare.</li>
          <li>"Hızı Hesapla" düğmesine bas.</li>
        </ol>
        {markEntries.length === 0 && (
          <p className="text-xs text-blue-600 mt-1">
            Şu an {markEntries.length} işaret var. Tıklayarak başla.
          </p>
        )}
      </div>

      {/* Kare navigasyonu */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>Kare: <span className="font-semibold tabular-nums text-foreground">{currentFrame}</span></span>
        <Button variant="outline" size="sm" className="h-7 px-2"
          onClick={() => goToFrame(currentFrame - 1)}>
          ← Önceki
        </Button>
        <Button variant="outline" size="sm" className="h-7 px-2"
          onClick={() => goToFrame(currentFrame + 1)}>
          Sonraki →
        </Button>
        <Input
          type="number"
          placeholder="kare no"
          value={frameInput}
          onChange={(e) => setFrameInput(e.target.value)}
          className="h-7 w-24"
        />
        <Button
          variant="secondary" size="sm" className="h-7 px-2"
          disabled={frameInput === ''}
          onClick={() => {
            const n = Number(frameInput)
            if (Number.isFinite(n)) goToFrame(n)
          }}
        >
          Git
        </Button>
        {marks[currentFrame] && (
          <span className="text-green-600 text-xs font-medium">✓ Bu kare işaretlendi</span>
        )}
      </div>

      {/* Video karesi + işaret canvas */}
      <CalibrationCanvas
        imageUrl={api.frameUrl(videoId, currentFrame)}
        points={canvasPoints}
        selectedId={null}
        onAdd={handleAdd}
        onMove={handleMove}
        onSelect={() => {}}
      />

      {/* İşaret listesi */}
      {markEntries.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">
            İşaretler ({markEntries.length}) — hepsinde AYNI teker olmalı:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {markEntries.map((m) => (
              <div
                key={m.frame}
                className={`flex items-center gap-1 rounded border px-2 py-0.5 text-xs cursor-pointer
                  ${m.frame === currentFrame ? 'border-primary bg-primary/10' : 'border-border bg-card'}`}
                onClick={() => setCurrentFrame(m.frame)}
              >
                <span className="tabular-nums">Kare {m.frame}</span>
                <button
                  className="text-muted-foreground hover:text-destructive"
                  onClick={(e) => { e.stopPropagation(); removeMark(m.frame) }}
                >
                  <Trash2 className="size-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Aksiyon butonları */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          disabled={markEntries.length < 2 || calcMutation.isPending}
          onClick={() => calcMutation.mutate()}
        >
          {calcMutation.isPending ? <Loader2 className="animate-spin" /> : <Target />}
          Hızı Hesapla
          {markEntries.length < 2 && ' (en az 2 işaret)'}
        </Button>
        {(markEntries.length > 0 || result) && (
          <Button variant="ghost" size="sm" onClick={handleReset}>
            Sıfırla
          </Button>
        )}
      </div>

      {calcMutation.isError && (
        <StatusBanner tone="error">{(calcMutation.error as Error).message}</StatusBanner>
      )}

      {/* Sonuç */}
      {result && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Operatör-Tekerlek Hızı</div>
              <div className="text-3xl font-bold tabular-nums leading-none">
                {result.value_kmh.toFixed(1)}
                <span className="text-base font-normal text-muted-foreground ml-1">km/h</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Güven Aralığı</div>
              <div className="text-lg font-semibold tabular-nums">
                ± {result.ci_kmh.toFixed(1)} km/h
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Güven</div>
              <ConfidenceBadge level={result.confidence_level} />
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">İşaret</div>
              <div className="text-sm tabular-nums">{result.mark_count} kare</div>
            </div>
          </div>

          {result.warnings.length > 0 && (
            <StatusBanner tone="warning">
              {result.warnings.join(' ')}
            </StatusBanner>
          )}

          <div className="text-[0.7rem] text-muted-foreground">
            Residual: {result.residual_kmh.toFixed(1)} km/h — ardışık çift hız std'si.
            Düşük residual = tutarlı işaretler.
          </div>

          <div className="border-t pt-3 space-y-2">
            <Button
              variant="outline"
              size="sm"
              disabled={regenerateMutation.isPending || regenerateMutation.isSuccess}
              onClick={() => regenerateMutation.mutate()}
            >
              {regenerateMutation.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
              {regenerateMutation.isSuccess ? 'Rapor güncellendi ✓' : 'Tekerlek Hızını PDF Raporuna Ekle'}
            </Button>
            {!regenerateMutation.isSuccess && (
              <p className="text-[0.7rem] text-amber-700">
                ⚠ Sonuç otomatik rapora eklenmez. Yukarıdaki düğme ile orijinal rapor
                korunarak birincil tekerlek hızı dahil yeni bir rapor (rapor_v2.pdf) oluşturulur.
              </p>
            )}
            {regenerateMutation.isError && (
              <StatusBanner tone="error">
                {(regenerateMutation.error as Error).message}
              </StatusBanner>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
