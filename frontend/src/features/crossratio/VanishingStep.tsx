import { useMutation } from '@tanstack/react-query'
import { Crosshair, Loader2, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { VanishingOut } from '@/lib/models'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { StatusBanner } from '@/components/common/StatusBanner'
import { cn } from '@/lib/utils'
import type { Pt } from './geometry'
import { bboxAt, frameUrl, useSelectedTrack, useVideoId } from './hooks'
import { MeasureCanvas, type Shape } from './MeasureCanvas'
import { FrameScrubber, StepGuide, type Check } from './parts'
import { usableVp, useCrossRatio } from './store'

const LANE_COLOR = '#facc15'
const TRAJ_COLOR = '#38bdf8'
const VP_COLOR = '#f472b6'

function vpText(v: VanishingOut) {
  if (!v.point) return 'sonsuzda (çizgiler görüntüde paralel)'
  return `(${v.point[0].toFixed(0)}, ${v.point[1].toFixed(0)}) px` +
    (v.sigma_major_px != null ? ` · ±${v.sigma_major_px.toFixed(1)} px` : '')
}

/** Adım 3 — Perspektif referansı (kaçış noktası): şerit çizgileri ve/veya araç izi. */
export function VanishingStep() {
  const videoId = useVideoId()
  const jobId = useCrossRatio((s) => s.jobId)
  const trackId = useCrossRatio((s) => s.trackId)
  const frameStart = useCrossRatio((s) => s.frameStart)
  const frameEnd = useCrossRatio((s) => s.frameEnd)
  const frame = useCrossRatio((s) => s.currentFrame)
  const setFrame = useCrossRatio((s) => s.setCurrentFrame)
  const laneLines = useCrossRatio((s) => s.laneLines)
  const laneDraft = useCrossRatio((s) => s.laneDraft)
  const addLanePoint = useCrossRatio((s) => s.addLanePoint)
  const removeLaneLine = useCrossRatio((s) => s.removeLaneLine)
  const clearLanes = useCrossRatio((s) => s.clearLanes)
  const useTrajectory = useCrossRatio((s) => s.useTrajectory)
  const setUseTrajectory = useCrossRatio((s) => s.setUseTrajectory)
  const preview = useCrossRatio((s) => s.vpPreview)
  const setPreview = useCrossRatio((s) => s.setVpPreview)
  const primary = useCrossRatio((s) => s.vpPrimary)
  const setPrimary = useCrossRatio((s) => s.setVpPrimary)
  const track = useSelectedTrack()

  const compute = useMutation({
    mutationFn: () => api.crossRatioVp(jobId!, trackId!, {
      lane_lines: laneLines.length >= 2 ? laneLines : [], use_trajectory: useTrajectory,
      frame_start: frameStart, frame_end: frameEnd,
    }),
    onSuccess: setPreview,
  })

  const shapes: Shape[] = []
  const b = bboxAt(track, frame)
  if (b) shapes.push({ kind: 'box', bbox: b, color: '#22c55e', dash: [5, 4] })
  const traj = preview?.trajectory
  if (traj && (primary === 'trajectory' || !preview?.lane)) {
    for (const l of traj.lines.slice(0, 60))
      shapes.push({ kind: 'line', a: l.start as Pt, b: l.end as Pt, color: TRAJ_COLOR, width: 1 })
  }
  laneLines.forEach((l, i) => {
    shapes.push({ kind: 'line', a: l[0], b: l[1], color: LANE_COLOR, width: 2.5, label: `Çizgi ${i + 1}` })
    shapes.push({ kind: 'point', p: l[0], color: LANE_COLOR, radius: 4 })
    shapes.push({ kind: 'point', p: l[1], color: LANE_COLOR, radius: 4 })
  })
  laneDraft.forEach((p) => shapes.push({ kind: 'point', p, color: LANE_COLOR, radius: 5, hollow: true, label: '2. ucu tıklayın' }))
  const chosen = usableVp(preview, primary)
  if (chosen?.point) {
    // Çizgileri VP'ye kadar uzat — operatör buluşmayı gözle görsün
    laneLines.forEach((l) => shapes.push({ kind: 'line', a: l[1], b: chosen.point as Pt, color: LANE_COLOR, width: 1, dash: [6, 5] }))
    shapes.push({ kind: 'vp', p: chosen.point as Pt, color: VP_COLOR, label: 'Perspektif referansı', sigmaPx: chosen.sigma_major_px })
  }

  const agreement = preview?.agreement
  const checks: Check[] = [
    {
      ok: laneLines.length >= 2 || useTrajectory ? true : laneLines.length === 1 ? false : null,
      text: 'En az bir kaynak: 2+ şerit çizgisi veya araç izi',
      hint: 'İkinci şerit/kenar çizgisini de işaretleyin ya da araç izini açın.',
    },
    { ok: preview ? chosen != null : null, text: 'Perspektif referansı hesaplandı',
      hint: preview?.trajectory_error ?? 'Hesaplama başarısız — çizgileri kontrol edin.' },
    {
      ok: agreement ? agreement.status === 'agree' : null,
      text: agreement ? `Şerit ve araç izi: ${agreement.status === 'agree' ? 'uyuşuyor' : agreement.status === 'disagree' ? 'ayrışıyor' : 'karşılaştırılamadı'}`
        : 'Çapraz kontrol (iki kaynak birlikte kullanılırsa)',
      hint: agreement?.message,
    },
    {
      ok: laneLines.length === 0 ? null : laneLines.length >= 3,
      text: `${laneLines.length} şerit çizgisi (3 önerilir)`,
      hint: 'Üçüncü çizgi, çizgilerin tek noktada buluşup buluşmadığını kontrol etmeyi sağlar.',
    },
  ]

  if (!videoId) return null
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-3">
        <MeasureCanvas imageUrl={frameUrl(videoId, frame)} shapes={shapes} onClick={addLanePoint} />
        <FrameScrubber value={frame} min={frameStart ?? 0} max={frameEnd ?? 0} onChange={setFrame} />
      </div>
      <div className="space-y-3">
        <StepGuide
          title="3 · Perspektif referansını belirleyin"
          instruction={<>Yol üzerinde, aracın gittiği yöne <b>paralel</b> uzanan şerit çizgilerini veya yol kenarlarını
            işaretleyin: her çizgi için <b>iki uca</b> tıklayın, uçları mümkün olduğunca <b>birbirinden uzak</b> seçin.
            Bu çizgilerin uzakta buluştuğu nokta, ölçümün perspektif referansıdır.</>}
          why={<>Kamera yolu eğik gördüğü için uzaktaki bir metre görüntüde yakındakinden kısa görünür. Paralel çizgilerin
            buluştuğu nokta (kaçış noktası) bu kısalmanın ne kadar olduğunu söyler; bilinen bir uzunlukla birleşince her
            piksel doğru bir metreye çevrilir. <b>Araç izi</b> seçeneği, aracın gövdesindeki noktaların hareketinden
            aynı referansı ek tıklama olmadan bulur — ikisi birlikte kullanılırsa birbirini doğrular.</>}
          checks={checks}
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Şerit / kenar çizgileri</span>
              {laneLines.length > 0 && (
                <button type="button" onClick={clearLanes} className="text-xs text-muted-foreground hover:text-red-600">Tümünü sil</button>
              )}
            </div>
            {laneLines.length === 0 && laneDraft.length === 0 && (
              <p className="text-xs text-muted-foreground">Karede bir çizginin ilk ucuna tıklayarak başlayın.</p>
            )}
            {laneLines.map((_, i) => (
              <div key={i} className="flex items-center justify-between rounded-md border px-2.5 py-1 text-sm">
                <span className="flex items-center gap-2"><span className="size-2.5 rounded-full" style={{ background: LANE_COLOR }} />Çizgi {i + 1}</span>
                <button type="button" onClick={() => removeLaneLine(i)} className="text-muted-foreground hover:text-red-600" title="Sil">
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            ))}
            <label className="flex items-start gap-2 rounded-md border p-2.5 text-sm">
              <input type="checkbox" className="mt-0.5" checked={useTrajectory} onChange={(e) => setUseTrajectory(e.target.checked)} />
              <span>Araç izinden de bul <span className="text-muted-foreground">(otomatik, ek tıklama yok — çapraz kontrol için önerilir)</span></span>
            </label>
            <Button className="w-full" onClick={() => compute.mutate()}
              disabled={compute.isPending || (laneLines.length < 2 && !useTrajectory)}>
              {compute.isPending ? <Loader2 className="size-4 animate-spin" /> : <Crosshair className="size-4" />}
              Perspektif referansını hesapla
            </Button>
            {compute.isError && <StatusBanner tone="error">{(compute.error as Error).message}</StatusBanner>}
          </div>

          {preview && (
            <div className="space-y-2">
              {([['lane', preview.lane, 'Şerit çizgileri', LANE_COLOR], ['trajectory', preview.trajectory, 'Araç izi', TRAJ_COLOR]] as const)
                .map(([key, v, name, color]) => v && (
                  <button key={key} type="button" onClick={() => setPrimary(key)}
                    className={cn('w-full rounded-md border p-2.5 text-left text-sm',
                      usableVp(preview, primary) === v ? 'border-primary bg-primary/5' : 'hover:bg-accent')}>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2 font-medium"><span className="size-2.5 rounded-full" style={{ background: color }} />{name}</span>
                      {usableVp(preview, primary) === v && <Badge variant="default">kullanılıyor</Badge>}
                    </div>
                    <div className="mt-0.5 text-xs tabular-nums text-muted-foreground">{vpText(v)}</div>
                    {key === 'trajectory' && (
                      <div className="text-xs text-muted-foreground">{v.n_inliers}/{v.n_lines} iz ortak noktada buluştu</div>
                    )}
                    {v.warnings.map((w, i) => <div key={i} className="mt-1 text-xs text-amber-800">⚠ {w}</div>)}
                  </button>
                ))}
              {preview.trajectory_error && useTrajectory && (
                <StatusBanner tone="warning">Araç izi: {preview.trajectory_error}</StatusBanner>
              )}
              {agreement && (
                <StatusBanner tone={agreement.status === 'agree' ? 'success' : agreement.status === 'disagree' ? 'warning' : 'info'}>
                  {agreement.message}
                </StatusBanner>
              )}
              {preview.lane && preview.trajectory && (
                <p className="text-[11px] text-muted-foreground">Kullanılacak kaynağı seçmek için karta tıklayın; diğeri çapraz kontrol olarak kalır.</p>
              )}
            </div>
          )}
        </StepGuide>
      </div>
    </div>
  )
}
