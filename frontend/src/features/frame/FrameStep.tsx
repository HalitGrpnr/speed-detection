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
        {/* İyi kare ipuçları */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 rounded-lg border bg-muted/20 px-4 py-3 text-xs">
          <span className="text-success">✓ Yol yüzeyi ve şerit çizgileri net</span>
          <span className="text-muted-foreground">✗ Sis veya hareket bulanıklığı</span>
          <span className="text-success">✓ Kamera sabit, titreşim yok</span>
          <span className="text-muted-foreground">✗ Araçlar tüm şeridi kapatmasın</span>
        </div>

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
            style={{
              background: `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) ${(frame / maxFrame) * 100}%, hsl(var(--muted)) ${(frame / maxFrame) * 100}%, hsl(var(--muted)) 100%)`,
            }}
            className="flex-1 h-1.5 cursor-pointer rounded-full appearance-none outline-none
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:size-4
              [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary
              [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:cursor-pointer
              [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-125
              [&::-moz-range-thumb]:size-4 [&::-moz-range-thumb]:rounded-full
              [&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:border-0
              [&::-moz-range-thumb]:cursor-pointer"
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
          Kare{' '}
          <span className="font-medium text-foreground tabular-nums">{frame}</span>
          {' / '}{maxFrame}
          {' · '}~<span className="tabular-nums">{timeSec.toFixed(2)}</span> sn
          {' · '}toplam:{' '}
          <span className="tabular-nums">
            {Math.floor(maxFrame / videoMeta.fps / 60)}:{String(Math.round(maxFrame / videoMeta.fps % 60)).padStart(2, '0')}
          </span>
        </p>

        <StepFooter />
      </CardContent>
    </Card>
  )
}
