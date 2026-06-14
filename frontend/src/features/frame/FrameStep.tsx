import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, ImageOff, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { StepFooter } from '@/components/common/StepFooter'

const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

export function FrameStep() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const selectedFrame = useWizard((s) => s.selectedFrame)
  const setSelectedFrame = useWizard((s) => s.setSelectedFrame)

  const maxFrame = Math.max(0, (videoMeta?.frame_count ?? 1) - 1)
  const [frame, setFrame] = useState(selectedFrame)
  const [previewFrame, setPreviewFrame] = useState(selectedFrame)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Kaydırırken istek yağmurunu engellemek için önizleme/store güncellemesi debounce'lanır.
  useEffect(() => {
    const t = setTimeout(() => {
      setPreviewFrame(frame)
      setSelectedFrame(frame)
    }, 200)
    return () => clearTimeout(t)
  }, [frame, setSelectedFrame])

  useEffect(() => {
    setLoading(true)
    setError(false)
  }, [previewFrame])

  if (!videoMeta) return null

  const update = (n: number) => setFrame(clamp(Number.isFinite(n) ? n : 0, 0, maxFrame))
  const timeSec = frame / (videoMeta.fps || 1)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 2 — Kalibrasyon Karesi Seç</CardTitle>
        <CardDescription>
          Yolun net göründüğü, kontrol noktası seçmeye uygun bir kare seçin.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="relative overflow-hidden rounded-lg border bg-canvas">
          <img
            src={api.frameUrl(videoMeta.video_id, previewFrame)}
            alt={`Kare ${previewFrame}`}
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false)
              setError(true)
            }}
            className="mx-auto block max-h-[55vh] w-full object-contain"
          />
          {loading && !error && (
            <div className="absolute inset-0 flex items-center justify-center bg-canvas/50">
              <Loader2 className="size-6 animate-spin text-white/70" />
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-white/70">
              <ImageOff className="size-6" />
              Kare yüklenemedi
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={() => update(frame - 1)} disabled={frame <= 0}>
            <ChevronLeft />
          </Button>
          <input
            type="range"
            min={0}
            max={maxFrame}
            value={frame}
            onChange={(e) => update(Number(e.target.value))}
            className="flex-1 accent-primary"
            aria-label="Kare seçici"
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => update(frame + 1)}
            disabled={frame >= maxFrame}
          >
            <ChevronRight />
          </Button>
          <Input
            type="number"
            min={0}
            max={maxFrame}
            value={frame}
            onChange={(e) => update(Number(e.target.value))}
            className="w-24"
          />
        </div>

        <p className="text-xs text-muted-foreground">
          Kare <span className="font-medium text-foreground tabular-nums">{frame}</span> / {maxFrame}
          {' · '}~{timeSec.toFixed(2)} sn
        </p>

        <StepFooter />
      </CardContent>
    </Card>
  )
}
