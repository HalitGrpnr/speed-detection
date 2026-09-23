import { useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Bot, Check as CheckIcon, Loader2, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { StatusBanner } from '@/components/common/StatusBanner'
import { cn } from '@/lib/utils'
import { perpDistance, sensitivityMPerPx, type Pt } from './geometry'
import { bboxAt, extendLine, frameUrl, useChosenVp, useMeasureLine, useSelectedTrack, useVideoId, windowPoints } from './hooks'
import { MeasureCanvas, type Shape } from './MeasureCanvas'
import { ContactPointDiagram, FrameScrubber, StepGuide, type Check } from './parts'
import { useCrossRatio } from './store'

const MARK_COLOR = '#22c55e'
const AUTO_COLOR = '#60a5fa'
const GHOST_COLOR = '#fb923c'
const GUIDE_COLOR = '#a78bfa'
const OFF_LINE_PX = 4
const FAR_M_PER_PX = 0.2
const SUGGEST_N = 6

/** Adım 5 — Aynı tekerin yere değdiği noktayı birkaç karede işaretle. */
export function ContactMarksStep() {
  const videoId = useVideoId()
  const jobId = useCrossRatio((s) => s.jobId)
  const trackId = useCrossRatio((s) => s.trackId)
  const frameStart = useCrossRatio((s) => s.frameStart)!
  const frameEnd = useCrossRatio((s) => s.frameEnd)!
  const frame = useCrossRatio((s) => s.currentFrame)
  const setFrame = useCrossRatio((s) => s.setCurrentFrame)
  const marks = useCrossRatio((s) => s.marks)
  const setMark = useCrossRatio((s) => s.setMark)
  const removeMark = useCrossRatio((s) => s.removeMark)
  const clearMarks = useCrossRatio((s) => s.clearMarks)
  const L = useCrossRatio((s) => s.length)
  const track = useSelectedTrack()
  const { vp, sigma } = useChosenVp()
  const line = useMeasureLine()

  const frames = Object.keys(marks).map(Number).sort((a, b) => a - b)
  const suggested = useMemo(() => {
    const pts = windowPoints(track, frameStart, frameEnd)
    if (pts.length === 0) return []
    const out = new Set<number>()
    for (let i = 0; i < SUGGEST_N; i++) out.add(pts[Math.round((i * (pts.length - 1)) / (SUGGEST_N - 1))].frame)
    return [...out]
  }, [track, frameStart, frameEnd])

  const autoMut = useMutation({
    mutationFn: () => api.autoContactPoints(jobId!, trackId!, 12),
    onSuccess: (r) => {
      for (const m of r.marks) {
        if (m.frame >= frameStart && m.frame <= frameEnd && !marks[m.frame])
          setMark(m.frame, m.pixel as Pt, 'auto')
      }
    },
  })

  const stats = (p: Pt) => {
    const off = line ? perpDistance(p, line) : null
    const sens = line && L.pointA && L.pointB ? sensitivityMPerPx(line, L.pointA, L.pointB, L.lengthM, p) : null
    return { off, sens }
  }

  const prevFrame = [...frames].reverse().find((f) => f < frame) ?? frames.find((f) => f > frame)
  const shapes: Shape[] = []
  const b = bboxAt(track, frame)
  if (b) shapes.push({ kind: 'box', bbox: b, color: '#22c55e', dash: [5, 4] })
  if (line) {
    const through = L.pointA ?? (frames.length ? marks[frames[0]].pixel : null)
    if (through) {
      const [a, e] = extendLine(line, through)
      shapes.push({ kind: 'line', a, b: e, color: GUIDE_COLOR, width: 1.5, dash: [7, 5] })
    }
  }
  if (prevFrame != null && prevFrame !== frame)
    shapes.push({ kind: 'point', p: marks[prevFrame].pixel, color: GHOST_COLOR, hollow: true, radius: 7, label: `kare ${prevFrame}` })
  const cur = marks[frame]
  if (cur) shapes.push({ kind: 'point', p: cur.pixel, color: cur.source === 'auto' ? AUTO_COLOR : MARK_COLOR, id: 'cur',
    label: cur.source === 'auto' ? 'öneri — onaylayın' : 'temas' })
  if (vp) shapes.push({ kind: 'vp', p: vp, color: '#f472b6', label: 'Perspektif referansı', sigmaPx: sigma })

  const all = frames.map((f) => ({ f, ...marks[f], ...stats(marks[f].pixel) }))
  const offBad = all.filter((m) => m.off != null && m.off > OFF_LINE_PX)
  const farBad = all.filter((m) => m.sens != null && m.sens > FAR_M_PER_PX)
  const autos = all.filter((m) => m.source === 'auto')
  const coverage = frames.length >= 2 ? (frames[frames.length - 1] - frames[0]) / Math.max(1, frameEnd - frameStart) : 0
  const curStats = cur ? stats(cur.pixel) : null

  const checks: Check[] = [
    { ok: frames.length >= 4 ? true : frames.length >= 2 ? false : null, text: `${frames.length} kare işaretli (en az 4 önerilir)`,
      hint: 'Önerilen karelerden devam edin — daha çok kare, tutarlılık kontrolü ve daha dar güven aralığı demektir.' },
    { ok: frames.length < 2 ? null : coverage >= 0.5, text: `İşaretler aralığın %${Math.round(coverage * 100)}'ini kapsıyor`,
      hint: 'İşaretleri aralığın başına ve sonuna yayın; kısa açıklık hızı belirsizleştirir.' },
    { ok: frames.length ? offBad.length === 0 : null, text: 'Tüm işaretler ölçüm çizgisi üzerinde',
      hint: `Kare ${offBad.map((m) => m.f).join(', ')}: işaret mor kılavuz çizgiden ${OFF_LINE_PX} px'ten fazla sapıyor — farklı tekere mi tıklandı?` },
    { ok: frames.length ? farBad.length === 0 : null, text: 'Araç her işaretli karede yeterince yakın',
      hint: `Kare ${farBad.map((m) => m.f).join(', ')}: 1 px ≈ ${Math.round(FAR_M_PER_PX * 100)} cm'den fazla — araç çok uzak; yakın kareleri tercih edin.` },
    { ok: autos.length === 0 ? (frames.length ? true : null) : false, text: 'Tüm işaretler operatör tarafından onaylı',
      hint: `${autos.length} otomatik öneri onay bekliyor — her birini karede kontrol edip "Onayla" deyin ya da düzeltin.` },
  ]

  if (!videoId) return null
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-3">
        <MeasureCanvas imageUrl={frameUrl(videoId, frame)} shapes={shapes}
          onClick={(p) => setMark(frame, p, 'manual')}
          onDrag={(_, p) => setMark(frame, p, marks[frame]?.source === 'auto' ? 'operator-confirmed' : 'manual')} />
        <FrameScrubber value={frame} min={frameStart} max={frameEnd} onChange={setFrame} marked={new Set(frames)} />
        {curStats && (
          <div className={cn('flex flex-wrap gap-x-4 gap-y-1 rounded-md border px-3 py-2 text-xs tabular-nums',
            (curStats.off ?? 0) > OFF_LINE_PX || (curStats.sens ?? 0) > FAR_M_PER_PX ? 'border-amber-300 bg-amber-50' : 'bg-muted/40')}>
            <span>Bu karedeki işaret:</span>
            {curStats.off != null && <span>çizgiden sapma <b>{curStats.off.toFixed(1)} px</b></span>}
            {curStats.sens != null && <span>1 px ≈ <b>{(curStats.sens * 100).toFixed(1)} cm</b></span>}
          </div>
        )}
      </div>
      <div className="space-y-3">
        <StepGuide
          title="5 · Tekerlek temas noktalarını işaretleyin"
          instruction={<>Aralıktaki birkaç karede, <b>hep aynı tekerleğin</b> (önerilen: 4. adımda işaretlediğiniz tarafın
            arka tekeri) <b>yere değdiği noktaya</b> tıklayın. Mor kesikli çizgi, işaretlerin üzerine düşmesi gereken
            ölçüm çizgisidir; turuncu halka bir önceki işaretinizdir.</>}
          why={<>Her işaretin gerçek konumu (metre) perspektif referansı ve bilinen uzunlukla hesaplanır; konumların zamana
            göre eğimi hızdır. Kutu alt kenarı yerine gerçek teker–zemin temasını kullanmak, gövde yüksekliğinden gelen
            sistematik hatayı ortadan kaldırır. Yakın kareler daha hassastır: uzaktaki bir pikselin metre karşılığı büyüktür.</>}
          checks={checks}
        >
          <ContactPointDiagram />
          <div>
            <div className="mb-1 text-xs font-medium text-muted-foreground">Önerilen kareler</div>
            <div className="flex flex-wrap gap-1.5">
              {suggested.map((f) => (
                <button key={f} type="button" onClick={() => setFrame(f)}
                  className={cn('rounded-md border px-2 py-0.5 text-xs tabular-nums',
                    f === frame ? 'border-primary bg-primary/10' : 'hover:bg-accent',
                    marks[f] && 'border-success/60 text-success')}>
                  {marks[f] && '✓ '}{f}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => autoMut.mutate()} disabled={autoMut.isPending}>
              {autoMut.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Bot className="size-3.5" />}
              Otomatik öneri getir
            </Button>
            {frames.length > 0 && <Button size="sm" variant="ghost" onClick={clearMarks}>Tümünü sil</Button>}
          </div>
          {autoMut.isError && <StatusBanner tone="error">{(autoMut.error as Error).message}</StatusBanner>}
          {autoMut.isSuccess && (
            <p className="text-[11px] text-muted-foreground">
              Öneriler mavi gösterilir ve klasik görüntü işlemeyle bulunur — kutu kenarına kayabilir. Her birini kontrol edin.
            </p>
          )}
          {all.length > 0 && (
            <div className="max-h-56 overflow-auto rounded-md border">
              <table className="w-full text-xs tabular-nums">
                <thead className="bg-muted/60 text-muted-foreground">
                  <tr><th className="px-2 py-1 text-left">Kare</th><th className="px-2 py-1 text-right">Sapma</th><th className="px-2 py-1 text-right">1 px ≈</th><th /></tr>
                </thead>
                <tbody>
                  {all.map((m) => (
                    <tr key={m.f} className={cn('border-t', m.f === frame && 'bg-primary/5')}>
                      <td className="px-2 py-1">
                        <button type="button" className="underline-offset-2 hover:underline" onClick={() => setFrame(m.f)}>{m.f}</button>
                        {m.source === 'auto' && <span className="ml-1 text-blue-600">öneri</span>}
                      </td>
                      <td className={cn('px-2 py-1 text-right', m.off != null && m.off > OFF_LINE_PX && 'font-semibold text-amber-700')}>
                        {m.off != null ? `${m.off.toFixed(1)} px` : '—'}
                      </td>
                      <td className={cn('px-2 py-1 text-right', m.sens != null && m.sens > FAR_M_PER_PX && 'font-semibold text-amber-700')}>
                        {m.sens != null ? `${(m.sens * 100).toFixed(1)} cm` : '—'}
                      </td>
                      <td className="px-1 py-1 text-right">
                        {m.source === 'auto' && (
                          <button type="button" title="Onayla" className="mr-1 text-success"
                            onClick={() => setMark(m.f, m.pixel, 'operator-confirmed')}>
                            <CheckIcon className="inline size-3.5" />
                          </button>
                        )}
                        <button type="button" title="Sil" className="text-muted-foreground hover:text-red-600" onClick={() => removeMark(m.f)}>
                          <Trash2 className="inline size-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </StepGuide>
      </div>
    </div>
  )
}
