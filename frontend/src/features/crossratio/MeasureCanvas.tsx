import { useCallback, useEffect, useRef, useState } from 'react'
import { Maximize2, ZoomIn, ZoomOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { edgePointToward, type Pt } from './geometry'

/**
 * T28 — Cross-ratio sihirbazı için ölçüm canvas'ı. Kare görüntüsünün üzerine bildirimsel
 * şekiller çizer; tıklamaları görüntü pikseline çevirir. Zoom/pan davranışı
 * CalibrationCanvas ile aynıdır (tekerlek teması piksel hassasiyeti ister).
 */
export type Shape =
  | { kind: 'line'; a: Pt; b: Pt; color: string; width?: number; dash?: number[]; label?: string }
  | { kind: 'point'; p: Pt; color: string; radius?: number; label?: string; hollow?: boolean; id?: string }
  | { kind: 'box'; bbox: readonly number[]; color: string; label?: string; dash?: number[] }
  | { kind: 'vp'; p: Pt; color: string; label?: string; sigmaPx?: number | null }

const MIN_ZOOM = 1
const MAX_ZOOM = 8
const HIT = 10
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

interface Props {
  imageUrl: string
  shapes: Shape[]
  onClick?: (p: Pt) => void
  /** id'li noktalar sürüklenebilir; bırakıldığında son konum bildirilir. */
  onDrag?: (id: string, p: Pt) => void
  cursor?: string
  className?: string
}

export function MeasureCanvas({ imageUrl, shapes, onClick, onDrag, cursor = 'crosshair', className }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const dragRef = useRef<string | null>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [ready, setReady] = useState(false)
  // Yüklenen görüntü state'te: kare değişince çizim MUTLAKA yeni görüntüyle tetiklenir
  // (yalnızca ref tutulursa eski kare ekranda kalır — adli araçta yanlış kareye işaret riski).
  const [loaded, setLoaded] = useState<HTMLImageElement | null>(null)
  const [hoverHandle, setHoverHandle] = useState(false)
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
    const maxH = window.innerHeight * 0.62
    setFitScale(Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1))
  }, [])

  // Kare değişince zoom korunur (aynı bölgeye art arda işaret koymak için).
  useEffect(() => {
    const img = new Image()
    img.onload = () => {
      const first = imgRef.current == null
      imgRef.current = img
      if (first) layout()
      setLoaded(img)
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
    const img = loaded
    if (!canvas || !img || !ready) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const W = img.naturalWidth
    const H = img.naturalHeight
    // Retina ekranlarda keskin görüntü: tampon dpr kat, CSS boyutu mantıksal piksel
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(W * scale * dpr)
    canvas.height = Math.round(H * scale * dpr)
    canvas.style.width = `${W * scale}px`
    canvas.style.height = `${H * scale}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    const CW = W * scale
    const CH = H * scale
    ctx.drawImage(img, 0, 0, CW, CH)
    const S = (p: Pt): Pt => [p[0] * scale, p[1] * scale]

    const label = (text: string, at: Pt, color: string) => {
      ctx.font = '600 12px Inter, system-ui, sans-serif'
      const w = ctx.measureText(text).width + 10
      const x = clamp(at[0] + 8, 2, CW - w - 2)
      const y = clamp(at[1] - 22, 2, CH - 20)
      ctx.fillStyle = 'rgba(15,23,42,0.85)'
      ctx.fillRect(x, y, w, 18)
      ctx.strokeStyle = color
      ctx.lineWidth = 1
      ctx.strokeRect(x, y, w, 18)
      ctx.fillStyle = '#fff'
      ctx.fillText(text, x + 5, y + 13)
    }

    for (const s of shapes) {
      ctx.save()
      if (s.kind === 'line') {
        ctx.strokeStyle = s.color
        ctx.lineWidth = s.width ?? 2
        ctx.setLineDash(s.dash ?? [])
        ctx.beginPath()
        ctx.moveTo(...S(s.a))
        ctx.lineTo(...S(s.b))
        ctx.stroke()
        if (s.label) label(s.label, S(s.b), s.color)
      } else if (s.kind === 'box') {
        const [x1, y1, x2, y2] = s.bbox
        ctx.strokeStyle = s.color
        ctx.lineWidth = 2
        ctx.setLineDash(s.dash ?? [])
        ctx.strokeRect(x1 * scale, y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale)
        if (s.label) label(s.label, [x1 * scale - 8, y1 * scale], s.color)
      } else if (s.kind === 'point') {
        const r = s.radius ?? 6
        const [x, y] = S(s.p)
        ctx.lineWidth = 2
        ctx.strokeStyle = '#0f172a'
        ctx.fillStyle = s.color
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        if (s.hollow) {
          ctx.strokeStyle = s.color
          ctx.setLineDash([3, 3])
          ctx.stroke()
        } else {
          ctx.fill()
          ctx.stroke()
        }
        // Artı işareti — piksel merkezini göster
        ctx.setLineDash([])
        ctx.strokeStyle = s.hollow ? s.color : '#fff'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(x - r - 4, y); ctx.lineTo(x + r + 4, y)
        ctx.moveTo(x, y - r - 4); ctx.lineTo(x, y + r + 4)
        ctx.stroke()
        if (s.label) label(s.label, [x, y], s.color)
      } else if (s.kind === 'vp') {
        const inside = s.p[0] >= 0 && s.p[1] >= 0 && s.p[0] <= W && s.p[1] <= H
        if (inside) {
          const [x, y] = S(s.p)
          if (s.sigmaPx && s.sigmaPx * scale > 4) {
            ctx.strokeStyle = s.color
            ctx.globalAlpha = 0.5
            ctx.setLineDash([4, 4])
            ctx.beginPath()
            ctx.arc(x, y, s.sigmaPx * scale * 2, 0, Math.PI * 2)
            ctx.stroke()
            ctx.globalAlpha = 1
            ctx.setLineDash([])
          }
          ctx.strokeStyle = s.color
          ctx.lineWidth = 3
          ctx.beginPath()
          ctx.moveTo(x - 12, y); ctx.lineTo(x + 12, y)
          ctx.moveTo(x, y - 12); ctx.lineTo(x, y + 12)
          ctx.stroke()
          if (s.label) label(s.label, [x, y], s.color)
        } else {
          // Ekran dışı: kenarda VP yönünü gösteren ok
          const e = S(edgePointToward(s.p, W, H))
          const t = S(s.p)
          const ang = Math.atan2(t[1] - e[1], t[0] - e[0])
          ctx.fillStyle = s.color
          ctx.translate(e[0], e[1])
          ctx.rotate(ang)
          ctx.beginPath()
          ctx.moveTo(12, 0); ctx.lineTo(-8, -9); ctx.lineTo(-8, 9)
          ctx.closePath()
          ctx.fill()
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
          label(`${s.label ?? 'Kaçış noktası'} — ekran dışında`, e, s.color)
        }
      }
      ctx.restore()
    }
  }, [shapes, scale, ready, loaded])

  useEffect(() => {
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const oldScale = fitRef.current * zoomRef.current
      const newZoom = clamp(zoomRef.current * (e.deltaY < 0 ? 1.15 : 1 / 1.15), MIN_ZOOM, MAX_ZOOM)
      if (newZoom === zoomRef.current) return
      const wr = wrap.getBoundingClientRect()
      const cr = canvas.getBoundingClientRect()
      const ix = (e.clientX - cr.left) / oldScale
      const iy = (e.clientY - cr.top) / oldScale
      const vx = e.clientX - wr.left
      const vy = e.clientY - wr.top
      setZoom(newZoom)
      requestAnimationFrame(() => {
        const ns = fitRef.current * newZoom
        wrap.scrollLeft = ix * ns - vx
        wrap.scrollTop = iy * ns - vy
      })
    }
    wrap.addEventListener('wheel', onWheel, { passive: false })
    return () => wrap.removeEventListener('wheel', onWheel)
  }, [])

  const zoomBy = (factor: number) => {
    const wrap = wrapRef.current
    const newZoom = clamp(zoomRef.current * factor, MIN_ZOOM, MAX_ZOOM)
    if (!wrap) { setZoom(newZoom); return }
    const os = fitRef.current * zoomRef.current
    const cx = (wrap.scrollLeft + wrap.clientWidth / 2) / os
    const cy = (wrap.scrollTop + wrap.clientHeight / 2) / os
    setZoom(newZoom)
    requestAnimationFrame(() => {
      const ns = fitRef.current * newZoom
      wrap.scrollLeft = cx * ns - wrap.clientWidth / 2
      wrap.scrollTop = cy * ns - wrap.clientHeight / 2
    })
  }

  const toImage = (e: React.MouseEvent<HTMLCanvasElement>): Pt => {
    // CSS pikselinden görüntü pikseline (dpr'den bağımsız)
    const r = canvasRef.current!.getBoundingClientRect()
    return [(e.clientX - r.left) / scale, (e.clientY - r.top) / scale]
  }

  const handleAt = (p: Pt): string | null => {
    if (!onDrag) return null
    for (let i = shapes.length - 1; i >= 0; i--) {
      const s = shapes[i]
      if (s.kind === 'point' && s.id && Math.hypot((s.p[0] - p[0]) * scale, (s.p[1] - p[1]) * scale) <= HIT)
        return s.id
    }
    return null
  }

  const img = imgRef.current
  const clampImg = (p: Pt): Pt =>
    img ? [clamp(p[0], 0, img.naturalWidth - 1), clamp(p[1], 0, img.naturalHeight - 1)] : p

  return (
    <div className={cn('relative', className)}>
      <div ref={wrapRef} className="max-h-[64vh] overflow-auto rounded-xl border bg-canvas shadow-card">
        {!ready && (
          <div className="flex h-72 items-center justify-center text-sm text-white/60">Kare yükleniyor…</div>
        )}
        <canvas
          ref={canvasRef}
          style={{ cursor: hoverHandle ? 'grab' : cursor }}
          className={cn('mx-auto block', !ready && 'hidden')}
          onMouseDown={(e) => {
            const p = toImage(e)
            const h = handleAt(p)
            if (h) { dragRef.current = h; return }
            onClick?.(clampImg(p))
          }}
          onMouseMove={(e) => {
            const p = toImage(e)
            if (dragRef.current) { onDrag?.(dragRef.current, clampImg(p)); return }
            setHoverHandle(handleAt(p) != null)
          }}
          onMouseUp={() => { dragRef.current = null }}
          onMouseLeave={() => { dragRef.current = null }}
        />
      </div>
      {ready && (
        <div className="absolute right-3 top-3 flex items-center gap-1 rounded-lg border border-white/15 bg-slate-900/85 p-1 text-white shadow-pop backdrop-blur">
          <button type="button" onClick={() => zoomBy(1 / 1.3)} disabled={zoom <= MIN_ZOOM + 1e-6}
            className="flex size-7 items-center justify-center rounded-md hover:bg-white/15 disabled:opacity-35" title="Uzaklaş">
            <ZoomOut className="size-4" />
          </button>
          <span className="min-w-[3rem] text-center text-xs tabular-nums">{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={() => zoomBy(1.3)} disabled={zoom >= MAX_ZOOM - 1e-6}
            className="flex size-7 items-center justify-center rounded-md hover:bg-white/15 disabled:opacity-35" title="Yakınlaş">
            <ZoomIn className="size-4" />
          </button>
          <button type="button" onClick={() => { setZoom(1); requestAnimationFrame(() => wrapRef.current?.scrollTo({ left: 0, top: 0 })) }}
            className="flex size-7 items-center justify-center rounded-md hover:bg-white/15" title="Sığdır (%100)">
            <Maximize2 className="size-4" />
          </button>
        </div>
      )}
    </div>
  )
}
