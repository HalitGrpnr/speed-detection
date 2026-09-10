import type { SpeedSeriesPoint } from '@/lib/models'

interface Props {
  points: SpeedSeriesPoint[]
  maxKmh: number
  medianKmh: number
  width?: number
  height?: number
}

export function SpeedSparkline({ points, maxKmh, medianKmh, width = 200, height = 64 }: Props) {
  if (points.length < 2) return null

  const pad = { top: 10, right: 4, bottom: 16, left: 4 }
  const W = width - pad.left - pad.right
  const H = height - pad.top - pad.bottom

  const tMin = points[0].t_s
  const tMax = points[points.length - 1].t_s
  const vMax = Math.max(maxKmh, 1)

  const px = (t: number) => pad.left + ((t - tMin) / (tMax - tMin || 1)) * W
  const py = (v: number) => pad.top + H - (v / vMax) * H

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${px(p.t_s).toFixed(1)},${py(p.speed_kmh).toFixed(1)}`)
    .join(' ')

  const medianY = py(medianKmh)
  const maxPoint = points.reduce((a, b) => (b.speed_kmh > a.speed_kmh ? b : a))
  const maxX = px(maxPoint.t_s)
  const maxY = py(maxPoint.speed_kmh)

  // Zaman ekseni etiketleri: başlangıç ve bitiş
  const tDur = tMax - tMin

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
      aria-label="Hız zaman serisi"
    >
      {/* Medyan çizgisi (gri kesik) */}
      <line
        x1={pad.left} y1={medianY}
        x2={pad.left + W} y2={medianY}
        stroke="#94a3b8" strokeWidth={1} strokeDasharray="3 2"
      />

      {/* Medyan etiketi */}
      <text
        x={pad.left + W - 1} y={medianY - 2}
        textAnchor="end" fontSize={7} fill="#64748b"
      >
        {medianKmh.toFixed(0)} km/h
      </text>

      {/* Hız eğrisi */}
      <path
        d={pathD}
        fill="none"
        stroke="#3b82f6"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* Max nokta (kırmızı) */}
      <circle cx={maxX} cy={maxY} r={2.5} fill="#ef4444" />
      <text
        x={maxX}
        y={maxY > pad.top + 10 ? maxY - 4 : maxY + 10}
        textAnchor="middle"
        fontSize={7}
        fill="#ef4444"
        fontWeight="600"
      >
        {maxKmh.toFixed(0)}
      </text>

      {/* Süre etiketi (alt merkez) */}
      {tDur > 0 && (
        <text
          x={pad.left + W / 2} y={height - 2}
          textAnchor="middle" fontSize={7} fill="#94a3b8"
        >
          {tDur.toFixed(1)} s
        </text>
      )}
    </svg>
  )
}
