import { useCallback, useEffect, useRef, useState } from 'react'
import { Maximize2, ZoomIn, ZoomOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ControlPoint, ControlPointSource } from '@/lib/models'

const RADIUS = 8
const QUAD_RADIUS = 10
const MIN_ZOOM = 1
const MAX_ZOOM = 8
const COLORS: Record<ControlPointSource, string> = {
  operator: '#f59e0b',
  auto: '#60a5fa',
  site_measurement: '#34d399',
  interpolated: '#a3e635',
  'auto-vanishing': '#c084fc',  // mor — T22
}
const SELECT = '#ef4444'
const REJECTED = '#f97316'
const QUAD_COLOR = '#a78bfa'
const GHOST_COLOR = '#ff6b35'
const ROAD_ANCHOR_COLOR = '#38bdf8'
const BRACKET_N_COLOR = '#f472b6'
const BRACKET_N1_COLOR = '#fb923c'
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

export type CanvasMode = 'point' | 'quad' | 'road-anchor' | 'bracket'
export type QuadCorners = [[number,number],[number,number],[number,number],[number,number]]

export interface BracketPoints {
  rear_n: [number, number] | null
  rear_n1: [number, number] | null
  front_n: [number, number] | null
  front_n1: [number, number] | null
}

interface Props {
  imageUrl: string
  points: ControlPoint[]
  selectedId: string | null
  rejectedIds?: Set<string>
  mode?: CanvasMode
  quadCorners?: QuadCorners | null
  /** T14: Ghost target overlay — önceki ön teker konumu (yarı saydam turuncu crosshair) */
  ghostTarget?: [number, number] | null
  /** T14: Bracket mode işaret noktaları — N (pembe) ve N+1 (turuncu) */
  bracketPoints?: BracketPoints | null
  /** T15: Yol yönü anchor noktaları (mavi) */
  roadAnchors?: [number, number][]
  /** T15: Transverse yön vektörü; ayarlıysa tüm kontrol noktaları + imlecinden kılavuz çizgisi */
  transverseDir?: [number, number] | null
  /** T15: İmleç konumu kılavuz çizgisi için (canvas koordinatları, skalasız) */
  cursorImagePx?: [number, number] | null
  /** T22: Yakınsama noktası (vanishing point) — mor artı işareti olarak gösterilir */
  vanishingPoint?: [number, number] | null
  /** T22: Sol şerit görselleştirme uç noktaları [bot, top] görüntü koordinatları */
  laneLineLeft?: [[number, number], [number, number]] | null
  /** T22: Sağ şerit görselleştirme uç noktaları */
  laneLineRight?: [[number, number], [number, number]] | null
  onAdd: (pixel: [number, number]) => void
  onMove: (id: string, pixel: [number, number]) => void
  onSelect: (id: string | null) => void
  onMoveQuadCorner?: (index: number, pixel: [number, number]) => void
  onCursorMove?: (px: [number, number] | null) => void
}

export function CalibrationCanvas({
  imageUrl, points, selectedId, rejectedIds,
  mode = 'point', quadCorners,
  ghostTarget, bracketPoints, roadAnchors, transverseDir, cursorImagePx,
  vanishingPoint, laneLineLeft, laneLineRight,
  onAdd, onMove, onSelect, onMoveQuadCorner, onCursorMove,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const dragRef = useRef<string | null>(null)
  const quadDragRef = useRef<number | null>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [ready, setReady] = useState(false)

  const scale = fitScale * zoom
  const fitRef = useRef(fitScale)
  const zoomRef = useRef(zoom)
  fitRef.current = fitScale
  zoomRef.current = zoom

  const layout = useCallback(() => {
    const img = imgRef.current
    const wrap = wrapRef.current
    if (!img || !wrap) return
    const maxW = wrap.clientWidth || 800
    const maxH = window.innerHeight * 0.66
    const s = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1)
    setFitScale(s)
  }, [])

  useEffect(() => {
    setReady(false)
    setZoom(1)
    const img = new Image()
    img.onload = () => {
      imgRef.current = img
      layout()
      setReady(true)
    }
    img.src = imageUrl
    return () => { img.onload = null }
  }, [imageUrl, layout])

  useEffect(() => {
    const onResize = () => layout()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [layout])

  useEffect(() => {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img || !ready) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = img.naturalWidth * scale
    canvas.height = img.naturalHeight * scale
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

    // T17: Kalibrasyon hull sınırı — pixel uzayında convex hull (≥3 non-rejected nokta)
    const validPts = points.filter((p) => !(rejectedIds?.has(p.id)))
    if (validPts.length >= 3) {
      const hull2d = _convexHull2D(validPts.map((p) => p.pixel as [number, number]))
      if (hull2d.length >= 3) {
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(hull2d[0][0] * scale, hull2d[0][1] * scale)
        for (let i = 1; i < hull2d.length; i++) {
          ctx.lineTo(hull2d[i][0] * scale, hull2d[i][1] * scale)
        }
        ctx.closePath()
        ctx.strokeStyle = 'rgba(34, 211, 238, 0.55)'
        ctx.lineWidth = 1.5
        ctx.setLineDash([6, 4])
        ctx.stroke()
        ctx.fillStyle = 'rgba(34, 211, 238, 0.06)'
        ctx.fill()
        ctx.setLineDash([])
        ctx.restore()
      }
    }

    // Kontrol noktaları
    points.forEach((pt, i) => {
      const cx = pt.pixel[0] * scale
      const cy = pt.pixel[1] * scale
      const selected = pt.id === selectedId
      const rejected = rejectedIds?.has(pt.id) ?? false
      const color = selected ? SELECT : rejected ? REJECTED : (COLORS[pt.source] ?? COLORS.operator)

      ctx.beginPath()
      ctx.arc(cx, cy, RADIUS, 0, Math.PI * 2)
      ctx.fillStyle = color + 'cc'
      ctx.fill()
      ctx.strokeStyle = selected ? SELECT : rejected ? REJECTED : '#fff'
      ctx.lineWidth = selected ? 2.5 : rejected ? 2 : 1.5
      ctx.stroke()

      if (rejected) {
        const d = RADIUS * 0.55
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.moveTo(cx - d, cy - d); ctx.lineTo(cx + d, cy + d)
        ctx.moveTo(cx + d, cy - d); ctx.lineTo(cx - d, cy + d)
        ctx.stroke()
      } else {
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 11px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(String(i + 1), cx, cy)
      }

      if (selected) {
        const label = `(${pt.world_m[0].toFixed(2)}, ${pt.world_m[1].toFixed(2)}) m`
        ctx.font = '11px sans-serif'
        const w = ctx.measureText(label).width + 10
        ctx.fillStyle = 'rgba(0,0,0,0.8)'
        ctx.fillRect(cx + RADIUS + 2, cy - 9, w, 18)
        ctx.fillStyle = '#fff'
        ctx.textAlign = 'left'
        ctx.fillText(label, cx + RADIUS + 7, cy)
      }
    })

    // T15: Transverse kılavuz çizgileri (kontrol noktalarından + imlecinden)
    if (transverseDir) {
      const [tx, ty] = transverseDir
      const W = img.naturalWidth
      const H = img.naturalHeight
      const drawGuide = (wx: number, wy: number, alpha: number) => {
        // canvas sınırında t aralığını bul
        let tMin = -1e6, tMax = 1e6
        if (Math.abs(tx) > 1e-9) {
          const tA = -wx / tx, tB = (W - wx) / tx
          tMin = Math.max(tMin, Math.min(tA, tB))
          tMax = Math.min(tMax, Math.max(tA, tB))
        }
        if (Math.abs(ty) > 1e-9) {
          const tA = -wy / ty, tB = (H - wy) / ty
          tMin = Math.max(tMin, Math.min(tA, tB))
          tMax = Math.min(tMax, Math.max(tA, tB))
        }
        const x1 = (wx + tMin * tx) * scale, y1 = (wy + tMin * ty) * scale
        const x2 = (wx + tMax * tx) * scale, y2 = (wy + tMax * ty) * scale
        ctx.save()
        ctx.globalAlpha = alpha
        ctx.strokeStyle = '#f97316'
        ctx.lineWidth = 1.5
        ctx.setLineDash([8, 5])
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()
      }
      // kontrol noktalarının her birinden kılavuz çiz
      points.forEach((pt) => drawGuide(pt.pixel[0], pt.pixel[1], 0.45))
      // imleç konumundan canlı önizleme kılavuzu
      if (cursorImagePx) drawGuide(cursorImagePx[0], cursorImagePx[1], 0.85)
    }

    // T15: Yol yönü anchor noktaları
    if (roadAnchors && roadAnchors.length > 0) {
      roadAnchors.forEach((anchor, i) => {
        const cx = anchor[0] * scale, cy = anchor[1] * scale
        ctx.beginPath()
        ctx.arc(cx, cy, 7, 0, Math.PI * 2)
        ctx.fillStyle = ROAD_ANCHOR_COLOR + 'cc'
        ctx.fill()
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 10px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(`Y${i + 1}`, cx, cy)
      })
      // İki anchor arasında yol yönü çizgisi
      if (roadAnchors.length >= 2) {
        ctx.save()
        ctx.globalAlpha = 0.5
        ctx.strokeStyle = ROAD_ANCHOR_COLOR
        ctx.lineWidth = 1.5
        ctx.setLineDash([6, 4])
        ctx.beginPath()
        ctx.moveTo(roadAnchors[0][0] * scale, roadAnchors[0][1] * scale)
        ctx.lineTo(roadAnchors[1][0] * scale, roadAnchors[1][1] * scale)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()
      }
    }

    // T14: Ghost target overlay — önceki ön teker konumu
    if (ghostTarget) {
      const [gx, gy] = [ghostTarget[0] * scale, ghostTarget[1] * scale]
      const gr = 14
      ctx.save()
      ctx.globalAlpha = 0.7
      ctx.strokeStyle = GHOST_COLOR
      ctx.lineWidth = 2
      ctx.setLineDash([5, 3])
      ctx.beginPath()
      ctx.arc(gx, gy, gr, 0, Math.PI * 2)
      ctx.stroke()
      ctx.setLineDash([])
      // Crosshair
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(gx - gr - 4, gy); ctx.lineTo(gx + gr + 4, gy)
      ctx.moveTo(gx, gy - gr - 4); ctx.lineTo(gx, gy + gr + 4)
      ctx.stroke()
      ctx.restore()
      // Etiket
      ctx.font = '10px sans-serif'
      ctx.fillStyle = GHOST_COLOR
      ctx.textAlign = 'left'
      ctx.fillText('Hedef', gx + gr + 6, gy - 4)
    }

    // T14: Bracket points
    if (bracketPoints) {
      const drawBracket = (px: [number,number] | null, label: string, color: string) => {
        if (!px) return
        const [cx, cy] = [px[0] * scale, px[1] * scale]
        ctx.beginPath()
        ctx.arc(cx, cy, 9, 0, Math.PI * 2)
        ctx.fillStyle = color + 'cc'
        ctx.fill()
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 9px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(label, cx, cy)
      }
      drawBracket(bracketPoints.rear_n,   'AN',   BRACKET_N_COLOR)
      drawBracket(bracketPoints.rear_n1,  'AN+1', BRACKET_N1_COLOR)
      drawBracket(bracketPoints.front_n,  'ÖN',   '#22d3ee')
      drawBracket(bracketPoints.front_n1, 'ÖN+1', '#2dd4bf')
    }

    // Dörtgen overlay
    if (quadCorners) {
      const sc = (p: [number,number]) => [p[0] * scale, p[1] * scale] as [number,number]
      const [a, b, c, d] = quadCorners.map(sc)

      // Yarı saydam dolgu
      ctx.beginPath()
      ctx.moveTo(a[0], a[1])
      ctx.lineTo(b[0], b[1])
      ctx.lineTo(c[0], c[1])
      ctx.lineTo(d[0], d[1])
      ctx.closePath()
      ctx.fillStyle = QUAD_COLOR + '22'
      ctx.fill()

      // Kenarlar
      ctx.strokeStyle = QUAD_COLOR
      ctx.lineWidth = 2
      ctx.setLineDash([])
      ctx.beginPath()
      ctx.moveTo(a[0], a[1])
      ctx.lineTo(b[0], b[1])
      ctx.lineTo(c[0], c[1])
      ctx.lineTo(d[0], d[1])
      ctx.closePath()
      ctx.stroke()

      // Köşe tutamaçları
      const labels = ['1', '2', '3', '4']
      ;[a, b, c, d].forEach(([cx, cy], i) => {
        ctx.beginPath()
        ctx.arc(cx, cy, QUAD_RADIUS, 0, Math.PI * 2)
        ctx.fillStyle = QUAD_COLOR
        ctx.fill()
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 11px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(labels[i], cx, cy)
      })
    }
    // T22: Şerit çizgisi overlay (tespit edilen yol çizgileri)
    const drawLaneLine = (pts: [[number,number],[number,number]] | null, color: string) => {
      if (!pts) return
      ctx.save()
      ctx.globalAlpha = 0.65
      ctx.strokeStyle = color
      ctx.lineWidth = 2.5
      ctx.setLineDash([10, 6])
      ctx.beginPath()
      ctx.moveTo(pts[0][0] * scale, pts[0][1] * scale)
      ctx.lineTo(pts[1][0] * scale, pts[1][1] * scale)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.restore()
    }
    drawLaneLine(laneLineLeft ?? null, '#22d3ee')    // cyan — sol şerit
    drawLaneLine(laneLineRight ?? null, '#86efac')   // açık yeşil — sağ şerit

    // T22: Yakınsama noktası (VP) işareti
    if (vanishingPoint) {
      const [vpx, vpy] = [vanishingPoint[0] * scale, vanishingPoint[1] * scale]
      const vr = 14
      ctx.save()
      ctx.globalAlpha = 0.85
      ctx.strokeStyle = '#c084fc'
      ctx.lineWidth = 2.5
      // Büyük artı işareti
      ctx.beginPath()
      ctx.moveTo(vpx - vr, vpy); ctx.lineTo(vpx + vr, vpy)
      ctx.moveTo(vpx, vpy - vr); ctx.lineTo(vpx, vpy + vr)
      ctx.stroke()
      // Daire
      ctx.beginPath()
      ctx.arc(vpx, vpy, vr * 0.5, 0, Math.PI * 2)
      ctx.strokeStyle = '#c084fc'
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.restore()
      // Etiket (görüntü sınırları içindeyse)
      if (vanishingPoint[0] >= 0 && vanishingPoint[1] >= 0) {
        ctx.font = '10px sans-serif'
        ctx.fillStyle = '#c084fc'
        ctx.textAlign = 'left'
        ctx.textBaseline = 'bottom'
        ctx.fillText('VP', vpx + vr + 3, vpy - 2)
      }
    }
  }, [points, selectedId, rejectedIds, scale, ready, quadCorners, ghostTarget, bracketPoints, roadAnchors, transverseDir, cursorImagePx, vanishingPoint, laneLineLeft, laneLineRight])

  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap) return
    const onWheel = (e: WheelEvent) => {
      // Pinch (ctrlKey=true on Mac) → zoom. İki parmak scroll → native pan.
      if (!e.ctrlKey) return
      const canvas = canvasRef.current
      if (!canvas) return
      e.preventDefault()
      const oldScale = fitRef.current * zoomRef.current
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
      const newZoom = clamp(zoomRef.current * factor, MIN_ZOOM, MAX_ZOOM)
      if (newZoom === zoomRef.current) return
      const wrapRect = wrap.getBoundingClientRect()
      const canvasRect = canvas.getBoundingClientRect()
      const imageX = (e.clientX - canvasRect.left) / oldScale
      const imageY = (e.clientY - canvasRect.top) / oldScale
      const cursorViewX = e.clientX - wrapRect.left
      const cursorViewY = e.clientY - wrapRect.top
      setZoom(newZoom)
      requestAnimationFrame(() => {
        const newScale = fitRef.current * newZoom
        wrap.scrollLeft = imageX * newScale - cursorViewX
        wrap.scrollTop = imageY * newScale - cursorViewY
      })
    }
    wrap.addEventListener('wheel', onWheel, { passive: false })
    return () => wrap.removeEventListener('wheel', onWheel)
  }, [])

  const zoomBy = (factor: number) => {
    const wrap = wrapRef.current
    const newZoom = clamp(zoomRef.current * factor, MIN_ZOOM, MAX_ZOOM)
    if (!wrap) { setZoom(newZoom); return }
    const oldScale = fitRef.current * zoomRef.current
    const centerX = (wrap.scrollLeft + wrap.clientWidth / 2) / oldScale
    const centerY = (wrap.scrollTop + wrap.clientHeight / 2) / oldScale
    setZoom(newZoom)
    requestAnimationFrame(() => {
      const newScale = fitRef.current * newZoom
      wrap.scrollLeft = centerX * newScale - wrap.clientWidth / 2
      wrap.scrollTop = centerY * newScale - wrap.clientHeight / 2
    })
  }

  const resetZoom = () => {
    setZoom(1)
    const wrap = wrapRef.current
    if (wrap) requestAnimationFrame(() => wrap.scrollTo({ left: 0, top: 0 }))
  }

  const toImage = (e: React.MouseEvent<HTMLCanvasElement>): [number, number] => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    const cx = (e.clientX - rect.left) * (canvas.width / rect.width)
    const cy = (e.clientY - rect.top) * (canvas.height / rect.height)
    return [cx / scale, cy / scale]
  }

  const findNear = (ix: number, iy: number): string | null => {
    for (let i = points.length - 1; i >= 0; i--) {
      const dx = (points[i].pixel[0] - ix) * scale
      const dy = (points[i].pixel[1] - iy) * scale
      if (Math.hypot(dx, dy) <= RADIUS + 4) return points[i].id
    }
    return null
  }

  const findNearQuadCorner = (ix: number, iy: number): number | null => {
    if (!quadCorners) return null
    for (let i = 0; i < quadCorners.length; i++) {
      const dx = (quadCorners[i][0] - ix) * scale
      const dy = (quadCorners[i][1] - iy) * scale
      if (Math.hypot(dx, dy) <= QUAD_RADIUS + 4) return i
    }
    return null
  }

  const onMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const [ix, iy] = toImage(e)

    if (mode === 'quad') {
      const qi = findNearQuadCorner(ix, iy)
      if (qi !== null) quadDragRef.current = qi
      return
    }

    // T15: road-anchor modu — tıklamalar onAdd'e yönlendirilir (CalibrationStep yönetir)
    // T14: bracket modu — tıklamalar onAdd'e yönlendirilir (CalibrationStep yönetir)
    if (mode === 'road-anchor' || mode === 'bracket') {
      onAdd([ix, iy])
      return
    }

    const hit = findNear(ix, iy)
    if (hit) {
      onSelect(hit)
      dragRef.current = hit
    } else {
      onAdd([ix, iy])
    }
  }

  const onMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const img = imgRef.current
    if (!img) return

    if (quadDragRef.current !== null) {
      const [ix, iy] = toImage(e)
      onMoveQuadCorner?.(quadDragRef.current, [
        clamp(ix, 0, img.naturalWidth - 1),
        clamp(iy, 0, img.naturalHeight - 1),
      ])
      return
    }

    // T15: imlec konumunu transverse guide preview için bildir
    if (transverseDir) {
      const [ix, iy] = toImage(e)
      onCursorMove?.([ix, iy])
    }

    if (!dragRef.current) return
    const [ix, iy] = toImage(e)
    onMove(dragRef.current, [
      clamp(ix, 0, img.naturalWidth - 1),
      clamp(iy, 0, img.naturalHeight - 1),
    ])
  }

  const endDrag = () => {
    dragRef.current = null
    quadDragRef.current = null
    onCursorMove?.(null)
  }

  const isQuadCornerNear = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (mode !== 'quad' || !quadCorners) return false
    const [ix, iy] = toImage(e)
    return findNearQuadCorner(ix, iy) !== null
  }

  const getCursor = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (mode === 'quad') return isQuadCornerNear(e) ? 'grab' : 'default'
    if (mode === 'road-anchor' || mode === 'bracket') return 'crosshair'
    return 'crosshair'
  }

  const [cursor, setCursor] = useState<string>('crosshair')

  return (
    <div className="relative">
      <div
        ref={wrapRef}
        className="max-h-[68vh] overflow-auto rounded-xl border bg-canvas shadow-card"
      >
        {!ready && (
          <div className="flex h-72 items-center justify-center text-sm text-white/60">
            Kare yükleniyor…
          </div>
        )}
        <canvas
          ref={canvasRef}
          onMouseDown={onMouseDown}
          onMouseMove={(e) => { onMouseMove(e); setCursor(getCursor(e)) }}
          onMouseUp={endDrag}
          onMouseLeave={endDrag}
          style={{ cursor }}
          className={cn('mx-auto block', !ready && 'hidden')}
        />
      </div>

      {ready && (
        <div className="absolute right-3 top-3 flex items-center gap-1 rounded-lg border border-white/15 bg-slate-900/85 p-1 text-white shadow-pop backdrop-blur">
          <button
            type="button"
            onClick={() => zoomBy(1 / 1.3)}
            disabled={zoom <= MIN_ZOOM + 1e-6}
            className="flex size-7 items-center justify-center rounded-md hover:bg-white/15 disabled:opacity-35"
            title="Uzaklaş"
          >
            <ZoomOut className="size-4" />
          </button>
          <span className="min-w-[3rem] text-center text-xs tabular-nums">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => zoomBy(1.3)}
            disabled={zoom >= MAX_ZOOM - 1e-6}
            className="flex size-7 items-center justify-center rounded-md hover:bg-white/15 disabled:opacity-35"
            title="Yakınlaş"
          >
            <ZoomIn className="size-4" />
          </button>
          <button
            type="button"
            onClick={resetZoom}
            className="flex size-7 items-center justify-center rounded-md hover:bg-white/15"
            title="Sığdır (%100)"
          >
            <Maximize2 className="size-4" />
          </button>
        </div>
      )}
    </div>
  )
}

// Andrew's monotone chain — 2D convex hull
function _cross(O: [number,number], A: [number,number], B: [number,number]): number {
  return (A[0] - O[0]) * (B[1] - O[1]) - (A[1] - O[1]) * (B[0] - O[0])
}

function _convexHull2D(pts: [number,number][]): [number,number][] {
  const n = pts.length
  if (n < 3) return [...pts]
  const sorted = [...pts].sort((a, b) => a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1])
  const lower: [number,number][] = []
  for (const p of sorted) {
    while (lower.length >= 2 && _cross(lower[lower.length-2], lower[lower.length-1], p) <= 0)
      lower.pop()
    lower.push(p)
  }
  const upper: [number,number][] = []
  for (let i = n - 1; i >= 0; i--) {
    const p = sorted[i]
    while (upper.length >= 2 && _cross(upper[upper.length-2], upper[upper.length-1], p) <= 0)
      upper.pop()
    upper.push(p)
  }
  lower.pop(); upper.pop()
  return [...lower, ...upper]
}
