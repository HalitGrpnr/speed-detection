import { useEffect, useRef, useState } from 'react'
import { CheckSquare, Loader2, Square, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { CalibrateResponse, ControlPoint, ControlPointSource, ProposedPoint } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RmsBadge } from '@/components/common/RmsBadge'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'
import { CalibrationCanvas, type CanvasMode, type QuadCorners } from './CalibrationCanvas'
import { PointsTable } from './PointsTable'
import { GridPresetBar } from './GridPresetBar'
import { AutoRefPanel } from './AutoRefPanel'

const makeId = (src: string) => `cp-${src}-${crypto.randomUUID().slice(0, 8)}`

type CalState =
  | { status: 'insufficient' }
  | { status: 'loading' }
  | { status: 'ok'; data: CalibrateResponse }
  | { status: 'error'; message: string }

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

  const addPoint = (pixel: [number, number]) => {
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
      source: 'auto',
      held_out: false,
    }))
    setControlPoints([...points, ...auto])
  }

  // Dörtgen overlay başlat — görüntü ortasına oranlı dikdörtgen
  const startQuad = () => {
    const iw = videoMeta.width
    const ih = videoMeta.height
    const x1 = iw * 0.30, y1 = ih * 0.35
    const x2 = iw * 0.70, y2 = ih * 0.35
    const x3 = iw * 0.70, y3 = ih * 0.65
    const x4 = iw * 0.30, y4 = ih * 0.65
    setQuadCorners([[x1,y1],[x2,y2],[x3,y3],[x4,y4]])
    setCanvasMode('quad')
  }

  const cancelQuad = () => {
    setQuadCorners(null)
    setCanvasMode('point')
  }

  const moveQuadCorner = (index: number, pixel: [number, number]) => {
    if (!quadCorners) return
    const next = quadCorners.map((c, i) => (i === index ? pixel : c)) as QuadCorners
    setQuadCorners(next)
  }

  const confirmQuad = () => {
    if (!quadCorners) return
    const w = parseFloat(widthRef.current?.value ?? '0')
    const h = parseFloat(heightRef.current?.value ?? '0')
    if (!w || !h || w <= 0 || h <= 0) return
    const worldCoords: [number, number][] = [[0,0],[w,0],[w,h],[0,h]]
    const newPoints: ControlPoint[] = quadCorners.map((pixel, i) => ({
      id: makeId('op'),
      pixel,
      world_m: worldCoords[i] as [number, number],
      source: 'operator',
      held_out: false,
    }))
    setControlPoints([...points, ...newPoints])
    setQuadDimDialog(false)
    cancelQuad()
  }

  const rejectedIds = new Set(
    cal.status === 'ok' ? cal.data.rejected_points.map((r) => r.id) : [],
  )

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
            <CalibrationCanvas
              imageUrl={api.frameUrl(videoMeta.video_id, selectedFrame)}
              points={points}
              selectedId={selectedId}
              rejectedIds={rejectedIds}
              mode={canvasMode}
              quadCorners={quadCorners}
              onAdd={addPoint}
              onMove={movePoint}
              onSelect={setSelectedId}
              onMoveQuadCorner={moveQuadCorner}
            />
            <p className="text-xs text-muted-foreground">
              {canvasMode === 'quad'
                ? <span className="text-violet-400 font-medium">
                    Dörtgen modu — 4 köşeyi sürükle, şerit/araç çizgilerine hizala. Hazır olunca sağdaki "Noktaları Ekle"ye bas.
                  </span>
                : <>
                    Tıkla = ekle · sürükle = taşı · <span className="font-medium">fare tekeri = yakınlaş</span> (hassas işaretleme) ·{' '}
                    <span className="text-amber-500">sarı operatör</span>,{' '}
                    <span className="text-blue-400">mavi otomatik</span>,{' '}
                    <span className="text-emerald-400">yeşil saha</span>,{' '}
                    <span className="text-orange-500">turuncu ✕ = dışlanan</span>.
                  </>
              }
            </p>
          </div>

          <div className="space-y-3">
            {/* Canlı RMS */}
            <div className="rounded-lg border p-3">
              <div className="mb-1 flex items-center justify-between">
                <span
                  className="text-sm font-medium"
                  title="Kalibrasyon hata payı: tıkladığınız noktaların girdiğiniz ölçümlerle ne kadar uyuştuğu. Küçük olması iyidir. (Teknik: re-projeksiyon RMS)"
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
                      <span title="Noktalar tek bir düz zemin oluşturmuyor; bazı noktalar zemin dışında (kaldırım, eğim vb.) olabilir. (Teknik: düzlemsellik uyarısı)">
                        {' '}· ⚠ noktalar aynı düzlemde görünmüyor
                      </span>
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

            {/* Dörtgen araçları */}
            {canvasMode === 'point' ? (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={startQuad}
              >
                <Square className="size-3.5" /> Dörtgen Çiz
              </Button>
            ) : (
              <div className="space-y-2 rounded-lg border border-violet-500/40 bg-violet-500/5 p-3">
                <p className="text-xs font-medium text-violet-400">Dörtgen modu aktif</p>
                <p className="text-xs text-muted-foreground">
                  Mor köşeleri sürükle → şerit/araç çizgilerine hizala.<br />
                  Köşe 1→(0,0) · 2→(G,0) · 3→(G,U) · 4→(0,U)
                </p>
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => setQuadDimDialog(true)}
                >
                  <CheckSquare className="size-3.5" /> Noktaları Ekle
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-muted-foreground"
                  onClick={cancelQuad}
                >
                  İptal
                </Button>
              </div>
            )}

            <Button
              variant="outline"
              size="sm"
              className="w-full"
              disabled={!selectedId}
              onClick={() => selectedId && deletePoint(selectedId)}
            >
              <Trash2 /> Seçili noktayı sil
            </Button>
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
