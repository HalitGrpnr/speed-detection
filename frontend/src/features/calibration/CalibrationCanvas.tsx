import { useCallback, useEffect, useRef, useState } from 'react'
import { Maximize2, ZoomIn, ZoomOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ControlPoint, ControlPointSource } from '@/lib/models'

const RADIUS = 8
const MIN_ZOOM = 1
const MAX_ZOOM = 8
const COLORS: Record<ControlPointSource, string> = {
  operator: '#f59e0b', // sarı
  auto: '#60a5fa', // mavi (M6)
  site_measurement: '#34d399', // yeşil (saha)
}
const SELECT = '#ef4444'
const REJECTED = '#f97316' // turuncu — RANSAC tarafından dışlanan noktalar
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

interface Props {
  imageUrl: string
  points: ControlPoint[]
  selectedId: string | null
  rejectedIds?: Set<string>
  onAdd: (pixel: [number, number]) => void
  onMove: (id: string, pixel: [number, number]) => void
  onSelect: (id: string | null) => void
}

/**
 * Kalibrasyon karesi üzerinde kontrol noktası tıklama/sürükleme + zoom.
 * scale = fitScale (kareyi alana sığdırır) × zoom (operatör yakınlaştırması).
 */
export function CalibrationCanvas({ imageUrl, points, selectedId, rejectedIds, onAdd, onMove, onSelect }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const dragRef = useRef<string | null>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [ready, setReady] = useState(false)

  const scale = fitScale * zoom
  // Wheel/buton zoom handler'ı en güncel değerleri okusun diye ref'ler.
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
    return () => {
      img.onload = null
    }
  }, [imageUrl, layout])

  useEffect(() => {
    const onResize = () => layout()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [layout])

  // Çizim (+ canvas boyutunu scale'e göre ayarla)
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
        // Reddedilen noktaya çarpı işareti çiz
        const d = RADIUS * 0.55
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.moveTo(cx - d, cy - d)
        ctx.lineTo(cx + d, cy + d)
        ctx.moveTo(cx + d, cy - d)
        ctx.lineTo(cx - d, cy + d)
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
  }, [points, selectedId, rejectedIds, scale, ready])

  // Cursor merkezli wheel zoom (passive:false gerekir → native listener)
  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap) return
    const onWheel = (e: WheelEvent) => {
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
    if (!wrap) {
      setZoom(newZoom)
      return
    }
    // Görünür merkez sabit kalsın
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

  const onMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const [ix, iy] = toImage(e)
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
    if (!dragRef.current || !img) return
    const [ix, iy] = toImage(e)
    onMove(dragRef.current, [
      clamp(ix, 0, img.naturalWidth - 1),
      clamp(iy, 0, img.naturalHeight - 1),
    ])
  }

  const endDrag = () => {
    dragRef.current = null
  }

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
          onMouseMove={onMouseMove}
          onMouseUp={endDrag}
          onMouseLeave={endDrag}
          className={cn('mx-auto block cursor-crosshair', !ready && 'hidden')}
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
