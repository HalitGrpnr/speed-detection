import { useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import type { ControlPoint, ControlPointSource } from '@/lib/models'

const RADIUS = 8
const COLORS: Record<ControlPointSource, string> = {
  operator: '#f59e0b', // sarı
  auto: '#60a5fa', // mavi (M6)
  site_measurement: '#34d399', // yeşil (saha)
}
const SELECT = '#ef4444'
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

interface Props {
  imageUrl: string
  points: ControlPoint[]
  selectedId: string | null
  onAdd: (pixel: [number, number]) => void
  onMove: (id: string, pixel: [number, number]) => void
  onSelect: (id: string | null) => void
}

/**
 * Kalibrasyon karesi üzerinde kontrol noktası tıklama/sürükleme.
 * (Legacy src/ui/static/calibration.js matematiğinin React portu.)
 */
export function CalibrationCanvas({ imageUrl, points, selectedId, onAdd, onMove, onSelect }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const dragRef = useRef<string | null>(null)
  const [scale, setScale] = useState(1)
  const [ready, setReady] = useState(false)

  const layout = useCallback(() => {
    const img = imgRef.current
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!img || !wrap || !canvas) return
    const maxW = wrap.clientWidth || 800
    const maxH = window.innerHeight * 0.55
    const s = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1)
    canvas.width = img.naturalWidth * s
    canvas.height = img.naturalHeight * s
    setScale(s)
  }, [])

  useEffect(() => {
    setReady(false)
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

  // Çizim
  useEffect(() => {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img || !ready) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, img.naturalWidth * scale, img.naturalHeight * scale)

    points.forEach((pt, i) => {
      const cx = pt.pixel[0] * scale
      const cy = pt.pixel[1] * scale
      const selected = pt.id === selectedId
      const color = selected ? SELECT : COLORS[pt.source] ?? COLORS.operator

      ctx.beginPath()
      ctx.arc(cx, cy, RADIUS, 0, Math.PI * 2)
      ctx.fillStyle = color + 'cc'
      ctx.fill()
      ctx.strokeStyle = selected ? SELECT : '#fff'
      ctx.lineWidth = selected ? 2.5 : 1.5
      ctx.stroke()

      ctx.fillStyle = '#fff'
      ctx.font = 'bold 11px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(i + 1), cx, cy)

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
  }, [points, selectedId, scale, ready])

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
    <div ref={wrapRef} className="overflow-hidden rounded-lg border bg-canvas">
      {!ready && (
        <div className="flex h-64 items-center justify-center text-sm text-white/60">
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
  )
}
