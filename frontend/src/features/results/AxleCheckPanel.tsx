import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, Ruler, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import type { ControlPoint } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBanner } from '@/components/common/StatusBanner'
import { CalibrationCanvas } from '@/features/calibration/CalibrationCanvas'

interface Props {
  jobId: string
  videoId: string
  trackId: number
  controlPoints: ControlPoint[]
  onClose: () => void
}

async function pollUntilDone(jobId: string): Promise<void> {
  for (let i = 0; i < 120; i++) {
    const s = await api.jobStatus(jobId)
    if (s.state === 'done') return
    if (s.state === 'error') throw new Error(s.error ?? 'Yeniden analiz başarısız.')
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error('Yeniden analiz zaman aşımına uğradı.')
}

/**
 * M9 — aks genişliği çapraz doğrulama. Sistemin otomatik confidence_level hesabına
 * dahil edilmez; yalnızca operatörün rapora elle ekleyebileceği destekleyici kanıttır.
 */
export function AxleCheckPanel({ jobId, videoId, trackId, controlPoints, onClose }: Props) {
  const [points, setPoints] = useState<ControlPoint[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [knownWidth, setKnownWidth] = useState(1.8)
  const [manualFrame, setManualFrame] = useState<number | null>(null)
  const [frameInput, setFrameInput] = useState('')

  const frameQuery = useQuery({
    queryKey: ['axleSuggestFrame', jobId, trackId],
    queryFn: () => api.axleSuggestFrame(jobId, trackId),
  })

  const checkMutation = useMutation({
    mutationFn: () => {
      const [left, right] = points
      return api.axleCheck(jobId, trackId, {
        pixel_left: left.pixel,
        pixel_right: right.pixel,
        known_width_m: knownWidth,
      })
    },
  })

  const recalibrateMutation = useMutation({
    mutationFn: async () => {
      const [left, right] = points
      const { job_id } = await api.recalibrate(jobId, {
        video_id: videoId,
        control_points: controlPoints,
        track_id: trackId,
        pixel_left: left.pixel,
        pixel_right: right.pixel,
        known_width_m: knownWidth,
      })
      await pollUntilDone(job_id)
      return job_id
    },
    onSuccess: (newJobId) => {
      useWizard.getState().setSourceJobId(jobId)
      useWizard.getState().setJobId(newJobId)
      onClose()
    },
  })

  const handleAdd = (pixel: [number, number]) => {
    setPoints((prev) => {
      if (prev.length >= 2) return prev // yalnızca sol + sağ tekerlek
      const id = prev.length === 0 ? 'axle_left' : 'axle_right'
      return [...prev, { id, pixel, world_m: [0, 0], source: 'operator', held_out: false }]
    })
  }

  const handleMove = (id: string, pixel: [number, number]) => {
    setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, pixel } : p)))
  }

  const handleReset = () => {
    setPoints([])
    setSelectedId(null)
    checkMutation.reset()
  }

  const goToFrame = (n: number) => {
    if (n < 0) return
    setManualFrame(n)
    handleReset() // farklı karede eski piksel noktaları geçersiz
  }

  const frameN = manualFrame ?? frameQuery.data?.frame_n

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Ruler className="size-4 text-muted-foreground" /> Aks Genişliği Doğrulama — Takip #{trackId}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Kapat
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        Önerilen karede aracın sol ve sağ tekerlek temas noktasını işaretleyin (tıklayarak ekleyin,
        sürükleyerek düzeltin), sonra aracın bilinen aks genişliğini girip hesaplayın. Öneri kare
        yalnızca bir başlangıç noktasıdır — gerekirse başka bir kare tercih edebilirsiniz.
      </p>

      {frameQuery.isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Aday kare belirleniyor…
        </div>
      )}

      {frameQuery.isError && (
        <StatusBanner tone="error">{(frameQuery.error as Error).message}</StatusBanner>
      )}

      {frameQuery.isSuccess && frameN == null && (
        <StatusBanner tone="warning">Bu takip için uygun bir kare bulunamadı.</StatusBanner>
      )}

      {frameN != null && (
        <>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>
              Kare: <span className="font-semibold tabular-nums text-foreground">{frameN}</span>
              {manualFrame == null && ' (öneri)'}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2"
              onClick={() => goToFrame(Math.max(0, frameN - 1))}
            >
              ← Önceki
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2"
              onClick={() => goToFrame(frameN + 1)}
            >
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
              variant="secondary"
              size="sm"
              className="h-7 px-2"
              disabled={frameInput === ''}
              onClick={() => {
                const n = Number(frameInput)
                if (Number.isFinite(n)) goToFrame(n)
              }}
            >
              Git
            </Button>
            {manualFrame != null && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                onClick={() => goToFrame(frameQuery.data?.frame_n ?? 0)}
              >
                Öneriye dön
              </Button>
            )}
          </div>

          <CalibrationCanvas
            imageUrl={api.frameUrl(videoId, frameN)}
            points={points}
            selectedId={selectedId}
            onAdd={handleAdd}
            onMove={handleMove}
            onSelect={setSelectedId}
          />
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted-foreground">
              Bilinen aks genişliği (m)
              <Input
                type="number"
                step="0.01"
                value={knownWidth}
                onChange={(e) => setKnownWidth(Number(e.target.value))}
                className="mt-1 h-8 w-32"
              />
            </label>
            <Button
              size="sm"
              disabled={points.length < 2 || checkMutation.isPending}
              onClick={() => checkMutation.mutate()}
            >
              {checkMutation.isPending ? <Loader2 className="animate-spin" /> : <Ruler />}
              Hesapla
            </Button>
            <Button variant="secondary" size="sm" onClick={handleReset}>
              Noktaları Sıfırla
            </Button>
          </div>
        </>
      )}

      {checkMutation.isError && (
        <StatusBanner tone="error">{(checkMutation.error as Error).message}</StatusBanner>
      )}

      {checkMutation.isSuccess && (
        <div className="rounded-lg border bg-card p-3 text-sm">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-xs text-muted-foreground">Ölçülen</div>
              <div className="font-semibold tabular-nums">
                {checkMutation.data.measured_m.toFixed(2)} m
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Bilinen</div>
              <div className="font-semibold tabular-nums">
                {checkMutation.data.known_m.toFixed(2)} m
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Fark</div>
              <div className="font-semibold tabular-nums">
                %{checkMutation.data.error_pct.toFixed(1)}
              </div>
            </div>
          </div>
          <p className="mt-2 text-[0.7rem] text-amber-700">
            ⚠ Bu sonuç PDF raporuna otomatik eklenmez (denetim kaydı olarak sunucuda saklanır) —
            bilirkişi gerekirse bu değerleri rapora elle ekleyebilir.
          </p>

          <div className="mt-3 border-t pt-3">
            <Button
              variant="secondary"
              size="sm"
              disabled={recalibrateMutation.isPending}
              onClick={() => recalibrateMutation.mutate()}
            >
              {recalibrateMutation.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Sparkles />
              )}
              Kalibrasyona Ekle ve Yeniden Analiz Et
            </Button>
            <p className="mt-1.5 text-[0.7rem] text-muted-foreground">
              Bu ölçümü yeni bir kalibrasyon noktası çifti olarak ekler, aracı tekrar tespit
              etmeden (mevcut takip kullanılır) hızları yeniden hesaplar. Sonuç <b>yeni bir
              analiz</b> olarak oluşur — bu ekrandaki mevcut sonuç/rapor değişmez.
            </p>
            {recalibrateMutation.isPending && (
              <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" /> Yeniden analiz ediliyor…
              </p>
            )}
            {recalibrateMutation.isError && (
              <StatusBanner tone="error">
                {(recalibrateMutation.error as Error).message}
              </StatusBanner>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
