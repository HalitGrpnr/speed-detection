import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, CheckSquare, Loader2, Square, Trash2, Target, Navigation, GitBranch } from 'lucide-react'
import { api } from '@/lib/api'
import type {
  CalibrateResponse, ControlPoint, ControlPointSource, InterpolatePointResponse, ProposedPoint,
} from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RmsBadge } from '@/components/common/RmsBadge'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { CalibrationCanvas, type BracketPoints, type CanvasMode, type QuadCorners } from './CalibrationCanvas'
import { PointsTable } from './PointsTable'
import { GridPresetBar } from './GridPresetBar'
import { AutoRefPanel } from './AutoRefPanel'

const makeId = (src: string) => `cp-${src}-${crypto.randomUUID().slice(0, 8)}`

type CalState =
  | { status: 'insufficient' }
  | { status: 'loading' }
  | { status: 'ok'; data: CalibrateResponse }
  | { status: 'error'; message: string }

// T15: 90° CCW rotasyon — yol yönünden transverse yön
function computeTransverseDir(p1: [number,number], p2: [number,number]): [number,number] {
  const dx = p2[0] - p1[0], dy = p2[1] - p1[1]
  const len = Math.hypot(-dy, dx)
  if (len < 1e-9) return [1, 0]
  return [-dy / len, dx / len]
}

export function CalibrationStep() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const selectedFrame = useWizard((s) => s.selectedFrame)
  const points = useWizard((s) => s.controlPoints)
  const setControlPoints = useWizard((s) => s.setControlPoints)
  const setCalibration = useWizard((s) => s.setCalibration)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [cal, setCal] = useState<CalState>({ status: 'insufficient' })
  const [canvasMode, setCanvasMode] = useState<CanvasMode>('point')
  const [quadCorners, setQuadCorners] = useState<QuadCorners | null>(null)
  const [quadDimDialog, setQuadDimDialog] = useState(false)
  const widthRef = useRef<HTMLInputElement>(null)
  const heightRef = useRef<HTMLInputElement>(null)

  // T15: Yol yönü anchor ve transverse guide
  const [roadAnchors, setRoadAnchors] = useState<[number,number][]>([])
  const [transverseDir, setTransverseDir] = useState<[number,number] | null>(null)
  const [cursorImagePx, setCursorImagePx] = useState<[number,number] | null>(null)

  // T14: Bracket mode
  // Faz sırası: rear_n → rear_n1 → front_n → front_n1 → hesapla
  type BracketPhase = 'rear_n' | 'rear_n1' | 'front_n' | 'front_n1' | 'result'
  const [ghostPoint, setGhostPoint] = useState<ControlPoint | null>(null)
  const [bracketPoints, setBracketPoints] = useState<BracketPoints>({ rear_n: null, rear_n1: null, front_n: null, front_n1: null })
  const [bracketPhase, setBracketPhase] = useState<BracketPhase>('rear_n')
  const [localFrame, setLocalFrame] = useState(selectedFrame)
  const [interpolateResult, setInterpolateResult] = useState<InterpolatePointResponse | null>(null)
  const [interpolating, setInterpolating] = useState(false)
  const [bracketError, setBracketError] = useState<string | null>(null)

  // Wizard'da selectedFrame değişince (Adım 2'ye geri dönülürse) senkronize et
  useEffect(() => {
    setLocalFrame(selectedFrame)
  }, [selectedFrame])

  // roadAnchors 2 olunca transverse yönü hesapla
  useEffect(() => {
    if (roadAnchors.length >= 2) {
      setTransverseDir(computeTransverseDir(roadAnchors[0], roadAnchors[1]))
    } else {
      setTransverseDir(null)
    }
  }, [roadAnchors])

  useEffect(() => {
    if (!videoMeta) return
    if (points.length < 4) {
      setCal({ status: 'insufficient' })
      setCalibration(null)
      return
    }
    setCal({ status: 'loading' })
    const t = setTimeout(async () => {
      try {
        const res = await api.calibrate({
          video_id: videoMeta.video_id,
          frame_n: selectedFrame,
          control_points: points,
        })
        setCal({ status: 'ok', data: res })
        setCalibration(res)
      } catch (e) {
        setCal({ status: 'error', message: (e as Error).message })
        setCalibration(null)
      }
    }, 400)
    return () => clearTimeout(t)
  }, [points, selectedFrame, videoMeta, setCalibration])

  if (!videoMeta) return null

  // ── Normal nokta ekleme ────────────────────────────────────────────────────
  const addPoint = (pixel: [number, number]) => {
    // T15: Road anchor modu
    if (canvasMode === 'road-anchor') {
      const next = [...roadAnchors, pixel].slice(-2) as [number,number][]
      setRoadAnchors(next)
      if (next.length >= 2) setCanvasMode('point')
      return
    }

    // T14: Bracket modu — 4 fazlı tıklama sırası
    if (canvasMode === 'bracket') {
      setBracketError(null)
      if (bracketPhase === 'rear_n') {
        setBracketPoints({ rear_n: pixel, rear_n1: null, front_n: null, front_n1: null })
        setBracketPhase('rear_n1')
      } else if (bracketPhase === 'rear_n1') {
        setBracketPoints((prev) => ({ ...prev, rear_n1: pixel }))
        setBracketPhase('front_n')
      } else if (bracketPhase === 'front_n') {
        setBracketPoints((prev) => ({ ...prev, front_n: pixel }))
        setBracketPhase('front_n1')
      } else if (bracketPhase === 'front_n1') {
        setBracketPoints((prev) => ({ ...prev, front_n1: pixel }))
        setBracketPhase('result')
      }
      return
    }

    const pt: ControlPoint = {
      id: makeId('op'),
      pixel,
      world_m: [0, 0],
      source: 'operator',
      held_out: false,
    }
    setControlPoints([...points, pt])
    setSelectedId(pt.id)
  }

  const movePoint = (id: string, pixel: [number, number]) =>
    setControlPoints(points.map((p) => (p.id === id ? { ...p, pixel } : p)))

  const updateWorld = (id: string, axis: 0 | 1, value: number) =>
    setControlPoints(
      points.map((p) =>
        p.id === id
          ? { ...p, world_m: (axis === 0 ? [value, p.world_m[1]] : [p.world_m[0], value]) as [number, number] }
          : p,
      ),
    )

  const updateSource = (id: string, source: ControlPointSource) =>
    setControlPoints(points.map((p) => (p.id === id ? { ...p, source } : p)))

  const deletePoint = (id: string) => {
    setControlPoints(points.filter((p) => p.id !== id))
    if (selectedId === id) setSelectedId(null)
    if (ghostPoint?.id === id) cancelBracket()
  }

  const applyGrid = (cols: number, rows: number, laneWidth: number, rowSpacing: number) => {
    const needed = cols * rows
    setControlPoints(
      points.map((p, i) =>
        i < needed
          ? { ...p, world_m: [(i % cols) * laneWidth, Math.floor(i / cols) * rowSpacing] as [number, number] }
          : p,
      ),
    )
  }

  const addProposals = (proposals: ProposedPoint[]) => {
    const auto: ControlPoint[] = proposals.map((pr) => ({
      id: makeId('auto'),
      pixel: pr.pixel,
      world_m: pr.world_m,
      source: 'auto' as const,
      held_out: false,
    }))
    setControlPoints([...points, ...auto])
  }

  // ── Dörtgen ───────────────────────────────────────────────────────────────
  const startQuad = () => {
    const iw = videoMeta.width, ih = videoMeta.height
    setQuadCorners([[iw*.30,ih*.35],[iw*.70,ih*.35],[iw*.70,ih*.65],[iw*.30,ih*.65]])
    setCanvasMode('quad')
  }

  const cancelQuad = () => { setQuadCorners(null); setCanvasMode('point') }

  const moveQuadCorner = (index: number, pixel: [number, number]) => {
    if (!quadCorners) return
    setQuadCorners(quadCorners.map((c, i) => (i === index ? pixel : c)) as QuadCorners)
  }

  const confirmQuad = () => {
    if (!quadCorners) return
    const w = parseFloat(widthRef.current?.value ?? '0')
    const h = parseFloat(heightRef.current?.value ?? '0')
    if (!w || !h || w <= 0 || h <= 0) return
    const worldCoords: [number, number][] = [[0,0],[w,0],[w,h],[0,h]]
    const newPoints: ControlPoint[] = quadCorners.map((pixel, i) => ({
      id: makeId('op'), pixel, world_m: worldCoords[i] as [number, number],
      source: 'operator', held_out: false,
    }))
    setControlPoints([...points, ...newPoints])
    setQuadDimDialog(false)
    cancelQuad()
  }

  // ── T15: Yol yönü anchor ─────────────────────────────────────────────────
  const startRoadAnchor = () => {
    setRoadAnchors([])
    setTransverseDir(null)
    setCanvasMode('road-anchor')
  }

  const clearRoadAnchors = () => {
    setRoadAnchors([])
    setTransverseDir(null)
    if (canvasMode === 'road-anchor') setCanvasMode('point')
  }

  // ── T14: Bracket mode ─────────────────────────────────────────────────────
  const startBracket = (pt: ControlPoint) => {
    setGhostPoint(pt)
    setBracketPoints({ rear_n: null, rear_n1: null, front_n: null, front_n1: null })
    setBracketPhase('rear_n')
    setInterpolateResult(null)
    setBracketError(null)
    setLocalFrame(selectedFrame)
    setCanvasMode('bracket')
  }

  const cancelBracket = () => {
    setGhostPoint(null)
    setBracketPoints({ rear_n: null, rear_n1: null, front_n: null, front_n1: null })
    setBracketPhase('rear_n')
    setInterpolateResult(null)
    setBracketError(null)
    setCanvasMode('point')
  }

  const resetBracketPoints = () => {
    setBracketPoints({ rear_n: null, rear_n1: null, front_n: null, front_n1: null })
    setBracketPhase('rear_n')
    setInterpolateResult(null)
    setBracketError(null)
  }

  const runInterpolation = async () => {
    const { rear_n, rear_n1, front_n, front_n1 } = bracketPoints
    if (!ghostPoint || !rear_n || !rear_n1) return
    setInterpolating(true)
    setBracketError(null)
    try {
      const res = await api.interpolatePoint(videoMeta.video_id, {
        frame_n_px: rear_n,
        frame_n1_px: rear_n1,
        target_px: ghostPoint.pixel,
        second_n_px: front_n ?? undefined,
        second_n1_px: front_n1 ?? undefined,
      })
      setInterpolateResult(res)
    } catch (e) {
      setBracketError((e as Error).message)
    } finally {
      setInterpolating(false)
    }
  }

  const confirmInterpolation = (useSecond: boolean) => {
    const { rear_n, rear_n1, front_n, front_n1 } = bracketPoints
    if (!ghostPoint || !interpolateResult || !rear_n || !rear_n1) return
    const px = useSecond && interpolateResult.second_interpolated_px
      ? interpolateResult.second_interpolated_px
      : interpolateResult.interpolated_px
    const pt: ControlPoint = {
      id: makeId('interp'),
      pixel: px,
      world_m: ghostPoint.world_m,
      source: 'interpolated',
      held_out: false,
      interpolation_meta: {
        rear_n_px: rear_n,
        rear_n1_px: rear_n1,
        front_n_px: front_n,
        front_n1_px: front_n1,
        target_px: ghostPoint.pixel,
        t: interpolateResult.t,
        ghost_id: ghostPoint.id,
        added: useSecond ? 'front' : 'rear',
      },
    }
    setControlPoints([...points, pt])
    setSelectedId(pt.id)
    cancelBracket()
  }

  const rejectedIds = new Set(
    cal.status === 'ok' ? cal.data.rejected_points.map((r) => r.id) : [],
  )

  const frameCount = videoMeta.frame_count
  const canvasImageUrl = api.frameUrl(videoMeta.video_id, localFrame)

  const readyToInterpolate = !!bracketPoints.rear_n && !!bracketPoints.rear_n1 && bracketPhase === 'result' && !interpolateResult

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 3 — Kontrol Noktaları</CardTitle>
        <CardDescription>
          Koyu canvas'a tıklayarak nokta ekleyin, sürükleyerek taşıyın; gerçek dünya
          koordinatlarını girin. Kalibrasyon kalitesi (hata payı) canlı hesaplanır.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="min-w-0 space-y-2">
            {/* Kare gezinme çubuğu — her modda aktif */}
            <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5">
              <button
                type="button"
                className="flex size-7 items-center justify-center rounded hover:bg-white/10 disabled:opacity-30"
                disabled={localFrame <= 0}
                onClick={() => setLocalFrame((f) => Math.max(0, f - 1))}
                title="Önceki kare (←)"
              >
                <ChevronLeft className="size-4" />
              </button>
              <span className="flex-1 text-center text-xs tabular-nums text-muted-foreground">
                Kare <span className="text-foreground font-medium">{localFrame}</span>
                <span className="text-white/30"> / {frameCount - 1}</span>
                {localFrame !== selectedFrame && (
                  <button
                    type="button"
                    className="ml-2 text-amber-400/80 hover:text-amber-400 underline-offset-2 hover:underline"
                    onClick={() => setLocalFrame(selectedFrame)}
                    title="Referans kareye dön"
                  >
                    referansa dön
                  </button>
                )}
              </span>
              <button
                type="button"
                className="flex size-7 items-center justify-center rounded hover:bg-white/10 disabled:opacity-30"
                disabled={localFrame >= frameCount - 1}
                onClick={() => setLocalFrame((f) => Math.min(frameCount - 1, f + 1))}
                title="Sonraki kare (→)"
              >
                <ChevronRight className="size-4" />
              </button>
            </div>
            {/* Bracket mode ek bilgi */}
            {canvasMode === 'bracket' && ghostPoint && (
              <div className="px-1 text-xs text-pink-400/80">
                Bracket hedef: {ghostPoint.world_m[0].toFixed(2)}, {ghostPoint.world_m[1].toFixed(2)} m
              </div>
            )}

            <CalibrationCanvas
              imageUrl={canvasImageUrl}
              points={canvasMode === 'bracket' ? [] : points}
              selectedId={selectedId}
              rejectedIds={rejectedIds}
              mode={canvasMode}
              quadCorners={quadCorners}
              ghostTarget={canvasMode === 'bracket' ? ghostPoint?.pixel ?? null : null}
              bracketPoints={canvasMode === 'bracket' ? bracketPoints : null}
              roadAnchors={roadAnchors.length > 0 ? roadAnchors : undefined}
              transverseDir={transverseDir}
              cursorImagePx={cursorImagePx}
              onAdd={addPoint}
              onMove={movePoint}
              onSelect={setSelectedId}
              onMoveQuadCorner={moveQuadCorner}
              onCursorMove={setCursorImagePx}
            />
            <p className="text-xs text-muted-foreground">
              {canvasMode === 'quad' ? (
                <span className="text-violet-400 font-medium">
                  Dörtgen modu — 4 köşeyi sürükle, şerit/araç çizgilerine hizala.
                </span>
              ) : canvasMode === 'road-anchor' ? (
                <span className="text-sky-400 font-medium">
                  Yol yönü modu — şerit çizgisi üzerine 2 nokta işaretle ({roadAnchors.length}/2)
                </span>
              ) : canvasMode === 'bracket' ? (
                <span className="text-pink-400 font-medium">
                  Bracket modu — turuncu hedefi referans alarak arka tekeri iki komşu karede işaretle (N, N+1)
                </span>
              ) : (
                <>
                  Tıkla = ekle · sürükle = taşı · <span className="font-medium">fare tekeri = yakınlaş</span> ·{' '}
                  <span className="text-amber-500">sarı operatör</span>,{' '}
                  <span className="text-blue-400">mavi otomatik</span>,{' '}
                  <span className="text-emerald-400">yeşil saha</span>,{' '}
                  <span className="text-lime-400">yeşil enterp.</span>,{' '}
                  <span className="text-orange-500">turuncu ✕ = dışlanan</span>.
                </>
              )}
            </p>
          </div>

          <div className="space-y-3">
            {/* Canlı RMS */}
            <div className="rounded-lg border p-3">
              <div className="mb-1 flex items-center justify-between">
                <span
                  className="text-sm font-medium"
                  title="Kalibrasyon hata payı: tıkladığınız noktaların girdiğiniz ölçümlerle ne kadar uyuştuğu."
                >
                  Kalibrasyon hata payı
                </span>
                {cal.status === 'loading' && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
              </div>
              {cal.status === 'insufficient' && (
                <p className="text-sm text-muted-foreground">En az 4 nokta gerekli ({points.length} var)</p>
              )}
              {cal.status === 'loading' && <RmsBadge rmsM={null} />}
              {cal.status === 'error' && <StatusBanner tone="error">{cal.message}</StatusBanner>}
              {cal.status === 'ok' && (
                <div className="space-y-1">
                  <RmsBadge rmsM={cal.data.rms_m} />
                  <p className="text-xs text-muted-foreground">
                    {cal.data.rejected_points.length > 0 ? (
                      <span className="text-orange-500 font-medium">
                        {cal.data.inlier_count} kabul, {cal.data.rejected_points.length} reddedildi
                      </span>
                    ) : (
                      <span>{cal.data.inlier_count}/{cal.data.point_count} nokta kullanıldı</span>
                    )}
                    {cal.data.planarity_warning && (
                      <span> · ⚠ noktalar aynı düzlemde görünmüyor</span>
                    )}
                  </p>
                </div>
              )}
            </div>

            <GridPresetBar pointCount={points.length} onApply={applyGrid} />
            <AutoRefPanel
              videoId={videoMeta.video_id}
              frame={selectedFrame}
              onProposals={addProposals}
            />

            {/* ── T15: Yol yönü kılavuzu ── */}
            {canvasMode !== 'bracket' && canvasMode !== 'quad' && (
              <div className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-3 space-y-2">
                <div className="flex items-center gap-1.5">
                  <Navigation className="size-3.5 text-sky-400" />
                  <span className="text-xs font-medium text-sky-400">Transverse Kılavuz (T15)</span>
                </div>
                {transverseDir ? (
                  <>
                    <p className="text-xs text-muted-foreground">
                      Kılavuz aktif — turuncu kesikli çizgiler şerit noktasının hangi yönde
                      olduğunu gösteriyor. İmleç konumundan canlı önizleme.
                    </p>
                    <p className="text-xs text-sky-300/70 tabular-nums">
                      yön: ({transverseDir[0].toFixed(3)}, {transverseDir[1].toFixed(3)})
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full text-muted-foreground"
                      onClick={clearRoadAnchors}
                    >
                      Kılavuzu Kaldır
                    </Button>
                  </>
                ) : canvasMode === 'road-anchor' ? (
                  <p className="text-xs text-sky-400">
                    Şerit çizgisi üzerinde 2 nokta işaretle ({roadAnchors.length}/2)…
                  </p>
                ) : (
                  <>
                    <p className="text-xs text-muted-foreground">
                      Şerit noktasını doğru yerleştirmek için perspektife duyarlı yol kılavuzu.
                      Önce 2 şerit noktası işaretle → kılavuz aktif.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={startRoadAnchor}
                    >
                      <Navigation className="size-3.5" /> Yol Yönü Tanımla
                    </Button>
                  </>
                )}
              </div>
            )}

            {/* ── T14: Bracket / enterpolasyon ── */}
            {canvasMode !== 'quad' && canvasMode !== 'road-anchor' && (
              canvasMode === 'bracket' ? (
                <div className="rounded-lg border border-pink-500/40 bg-pink-500/5 p-3 space-y-2">
                  <div className="flex items-center gap-1.5">
                    <GitBranch className="size-3.5 text-pink-400" />
                    <span className="text-xs font-medium text-pink-400">Bracket Modu</span>
                  </div>
                  {ghostPoint && (
                    <p className="text-xs text-muted-foreground">
                      Hedef (ön teker): <span className="text-pink-300">
                        ({ghostPoint.world_m[0].toFixed(2)}, {ghostPoint.world_m[1].toFixed(2)}) m
                      </span>
                    </p>
                  )}

                  {/* 4 adım göstergesi */}
                  <div className="text-xs space-y-1.5 py-1">
                    {([
                      ['rear_n',   'AN',   'Arka teker — N karesi (hedefin gerisinde)', '#f472b6'],
                      ['rear_n1',  'AN+1', 'Arka teker — N+1 karesi (hedefin ilerisinde)', '#fb923c'],
                      ['front_n',  'ÖN',   'Ön teker — N karesi (aynı kare)', '#22d3ee'],
                      ['front_n1', 'ÖN+1', 'Ön teker — N+1 karesi (aynı kare)', '#2dd4bf'],
                    ] as const).map(([key, label, desc, color]) => {
                      const val = bracketPoints[key as keyof BracketPoints]
                      const isActive = bracketPhase === key
                      return (
                        <div key={key} className={`flex items-center gap-2 rounded px-2 py-1 ${isActive ? 'bg-white/8' : ''}`}>
                          <span className="size-5 shrink-0 flex items-center justify-center rounded text-[9px] font-bold"
                            style={{ backgroundColor: color + '33', color }}>
                            {label}
                          </span>
                          <span className={`flex-1 ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}>{desc}</span>
                          <span className="tabular-nums" style={{ color: val ? color : undefined }}>
                            {val ? `(${val[0].toFixed(0)},${val[1].toFixed(0)})` : isActive ? '← tıkla' : '—'}
                          </span>
                        </div>
                      )
                    })}
                  </div>

                  {bracketError && <StatusBanner tone="error">{bracketError}</StatusBanner>}

                  {interpolateResult ? (
                    <>
                      <div className="rounded bg-white/5 border border-white/10 p-2 text-xs space-y-1">
                        <p className="text-white/60">t = <span className="text-white font-mono">{interpolateResult.t.toFixed(4)}</span>
                          {(interpolateResult.t < 0 || interpolateResult.t > 1) &&
                            <span className="text-orange-400 ml-1">⚠ aralık dışı</span>}
                        </p>
                        <p className="text-white/60">Arka teker: <span className="text-pink-400">
                          ({interpolateResult.interpolated_px[0].toFixed(1)}, {interpolateResult.interpolated_px[1].toFixed(1)})
                        </span></p>
                        {interpolateResult.second_interpolated_px && (
                          <p className="text-white/60">Ön teker: <span className="text-cyan-400">
                            ({interpolateResult.second_interpolated_px[0].toFixed(1)}, {interpolateResult.second_interpolated_px[1].toFixed(1)})
                          </span></p>
                        )}
                      </div>
                      {interpolateResult.second_interpolated_px && (
                        <Button size="sm" className="w-full bg-cyan-600 hover:bg-cyan-500"
                          onClick={() => confirmInterpolation(true)}>
                          Ön Tekeri Ekle (Point 3)
                        </Button>
                      )}
                      <Button size="sm" variant="outline" className="w-full"
                        onClick={() => confirmInterpolation(false)}>
                        Arka Tekeri Ekle
                      </Button>
                      <Button variant="ghost" size="sm" className="w-full text-muted-foreground"
                        onClick={resetBracketPoints}>
                        Yeniden İşaretle
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      className="w-full"
                      disabled={!readyToInterpolate || interpolating}
                      onClick={runInterpolation}
                    >
                      {interpolating && <Loader2 className="size-3.5 animate-spin" />}
                      Enterpolasyonu Hesapla
                    </Button>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-muted-foreground"
                    onClick={cancelBracket}
                  >
                    İptal
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  disabled={!selectedId}
                  title={selectedId ? 'Seçili noktayı hedef alarak alt-kare enterpolasyon' : 'Önce bir nokta seç'}
                  onClick={() => {
                    const pt = points.find((p) => p.id === selectedId)
                    if (pt) startBracket(pt)
                  }}
                >
                  <Target className="size-3.5" /> Bracket Enterpolasyon
                </Button>
              )
            )}

            {/* ── Dörtgen araçları ── */}
            {canvasMode === 'point' && (
              <Button variant="outline" size="sm" className="w-full" onClick={startQuad}>
                <Square className="size-3.5" /> Dörtgen Çiz
              </Button>
            )}
            {canvasMode === 'quad' && (
              <div className="space-y-2 rounded-lg border border-violet-500/40 bg-violet-500/5 p-3">
                <p className="text-xs font-medium text-violet-400">Dörtgen modu aktif</p>
                <p className="text-xs text-muted-foreground">
                  Mor köşeleri sürükle → şerit/araç çizgilerine hizala.<br />
                  Köşe 1→(0,0) · 2→(G,0) · 3→(G,U) · 4→(0,U)
                </p>
                <Button size="sm" className="w-full" onClick={() => setQuadDimDialog(true)}>
                  <CheckSquare className="size-3.5" /> Noktaları Ekle
                </Button>
                <Button variant="ghost" size="sm" className="w-full text-muted-foreground" onClick={cancelQuad}>
                  İptal
                </Button>
              </div>
            )}

            {canvasMode === 'point' && (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                disabled={!selectedId}
                onClick={() => selectedId && deletePoint(selectedId)}
              >
                <Trash2 /> Seçili noktayı sil
              </Button>
            )}
          </div>
        </div>

        <PointsTable
          points={points}
          selectedId={selectedId}
          rejectedPoints={cal.status === 'ok' ? cal.data.rejected_points : undefined}
          onSelect={setSelectedId}
          onUpdateWorld={updateWorld}
          onUpdateSource={updateSource}
          onDelete={deletePoint}
        />

        <StepFooter />
      </CardContent>

      {/* Dörtgen boyut dialogu */}
      {quadDimDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-80 rounded-xl border bg-card p-5 shadow-pop">
            <h3 className="mb-1 text-sm font-semibold">Dörtgenin gerçek dünya boyutları</h3>
            <p className="mb-4 text-xs text-muted-foreground">
              Köşe 1→(0,0) · 2→(G,0) · 3→(G,U) · 4→(0,U)
            </p>
            <div className="mb-4 grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium">Genişlik G (m)</label>
                <Input ref={widthRef} type="number" min="0.1" step="0.1" defaultValue="3.5" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium">Uzunluk U (m)</label>
                <Input ref={heightRef} type="number" min="0.1" step="0.1" defaultValue="3.0" />
              </div>
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={confirmQuad}>Noktaları Ekle</Button>
              <Button variant="outline" className="flex-1" onClick={() => setQuadDimDialog(false)}>İptal</Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
