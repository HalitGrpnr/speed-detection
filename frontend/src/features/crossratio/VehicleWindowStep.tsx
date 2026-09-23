import { useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { bboxBottomCenter, lineFitRms, type Pt } from './geometry'
import { bboxAt, CLASS_TR, frameUrl, useSelectedTrack, useVideoId, windowPoints } from './hooks'
import { MeasureCanvas, type Shape } from './MeasureCanvas'
import { FrameScrubber, StepGuide, type Check } from './parts'
import { useCrossRatio } from './store'

const MIN_WINDOW_POINTS = 6
const STRAIGHT_HINT_PX = 6

/** Adım 2 — Ölçülecek aracı ve düz gittiği kare aralığını seç. */
export function VehicleWindowStep() {
  const videoId = useVideoId()
  const tracks = useCrossRatio((s) => s.tracks)
  const trackId = useCrossRatio((s) => s.trackId)
  const selectTrack = useCrossRatio((s) => s.selectTrack)
  const frameStart = useCrossRatio((s) => s.frameStart)
  const frameEnd = useCrossRatio((s) => s.frameEnd)
  const setWindow = useCrossRatio((s) => s.setWindow)
  const frame = useCrossRatio((s) => s.currentFrame)
  const setFrame = useCrossRatio((s) => s.setCurrentFrame)
  const track = useSelectedTrack()

  const minF = Math.min(...tracks.map((t) => t.first_frame))
  const maxF = Math.max(...tracks.map((t) => t.last_frame))
  const inWindow = windowPoints(track, frameStart, frameEnd)
  const straightRms = useMemo(
    () => lineFitRms(inWindow.map((p) => bboxBottomCenter(p.bbox))),
    [inWindow],
  )

  const shapes: Shape[] = []
  for (const t of tracks) {
    const b = bboxAt(t, frame)
    if (!b) continue
    const sel = t.track_id === trackId
    shapes.push({ kind: 'box', bbox: b, color: sel ? '#22c55e' : '#94a3b8', dash: sel ? undefined : [5, 4],
      label: `#${t.track_id} ${CLASS_TR[t.vehicle_class] ?? t.vehicle_class}` })
  }
  if (track && inWindow.length > 1) {
    const path = inWindow.map((p) => bboxBottomCenter(p.bbox))
    for (let i = 1; i < path.length; i++)
      shapes.push({ kind: 'line', a: path[i - 1], b: path[i], color: '#22c55e', width: 1.5 })
  }

  const clickSelect = (p: Pt) => {
    const hit = tracks.find((t) => {
      const b = bboxAt(t, frame)
      return b && p[0] >= b[0] && p[0] <= b[2] && p[1] >= b[1] && p[1] <= b[3]
    })
    if (hit) selectTrack(hit.track_id)
  }

  const checks: Check[] = [
    { ok: trackId != null, text: 'Ölçülecek araç seçildi', hint: 'Karede aracın kutusuna tıklayın veya listeden seçin.' },
    {
      ok: track ? inWindow.length >= MIN_WINDOW_POINTS : null,
      text: `Aralıkta aracın en az ${MIN_WINDOW_POINTS} karesi var (${inWindow.length})`,
      hint: 'Aralığı genişletin — çok kısa aralık hem perspektif referansını hem hızı belirsizleştirir.',
    },
    {
      ok: straightRms == null ? null : straightRms <= STRAIGHT_HINT_PX,
      text: straightRms == null ? 'Düz gidiş kontrolü (en az 3 kare gerekir)'
        : `Araç izi bir doğruya oturuyor (sapma ≈ ${straightRms.toFixed(1)} px)`,
      hint: 'Araç bu aralıkta dönüyor ya da şerit değiştiriyor olabilir — yalnızca düz giden kısmı seçin. (Kutu tabanlı kaba ipucu; kesin kontrol sonuçta yapılır.)',
    },
  ]

  if (!videoId) return null
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-3">
        <MeasureCanvas imageUrl={frameUrl(videoId, frame)} shapes={shapes} onClick={clickSelect} cursor="pointer" />
        <FrameScrubber value={frame} min={minF} max={maxF} onChange={setFrame}
          highlight={frameStart != null && frameEnd != null ? [frameStart, frameEnd] : null} />
      </div>
      <div className="space-y-3">
        <StepGuide
          title="2 · Aracı ve düz gittiği aralığı seçin"
          instruction={<>Hızını ölçmek istediğiniz aracın kutusuna tıklayın. Sonra kaydırıcıyla aracın <b>düz bir
            doğru boyunca gittiği</b> kısmın başına ve sonuna gidip aralığı işaretleyin.</>}
          why={<>Yöntem aracın bu aralıkta düz gittiğini varsayar. Dönüş, şerit değiştirme veya çarpışma anı aralığa
            girerse ölçüm geçersizleşir. Kaza anından <i>önceki</i> düz yaklaşma kısmı genellikle en uygun aralıktır.</>}
          checks={checks}
        >
          <div className="max-h-44 space-y-1 overflow-auto">
            {tracks.map((t) => (
              <button key={t.track_id} type="button" onClick={() => { selectTrack(t.track_id); setFrame(t.first_frame) }}
                className={cn('flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-sm',
                  t.track_id === trackId ? 'border-success bg-success/10' : 'hover:bg-accent')}>
                <span>#{t.track_id} · {CLASS_TR[t.vehicle_class] ?? t.vehicle_class}</span>
                <span className="text-xs tabular-nums text-muted-foreground">kare {t.first_frame}–{t.last_frame}</span>
              </button>
            ))}
          </div>
          {track && (
            <div className="space-y-2 rounded-md border p-2.5">
              <div className="text-xs font-medium text-muted-foreground">Düz-gidiş aralığı</div>
              <div className="flex items-center gap-2 text-sm tabular-nums">
                <span>Başlangıç: <b>{frameStart ?? '—'}</b></span>
                <span className="text-muted-foreground">·</span>
                <span>Bitiş: <b>{frameEnd ?? '—'}</b></span>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" className="flex-1"
                  onClick={() => setWindow(frame, frameEnd != null && frameEnd > frame ? frameEnd : track.last_frame)}>
                  Başlangıç = bu kare
                </Button>
                <Button size="sm" variant="secondary" className="flex-1"
                  onClick={() => setWindow(frameStart != null && frameStart < frame ? frameStart : track.first_frame, frame)}>
                  Bitiş = bu kare
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Aralığı değiştirmek sonraki adımlardaki perspektif referansını ve işaretleri sıfırlar.
              </p>
            </div>
          )}
        </StepGuide>
      </div>
    </div>
  )
}
