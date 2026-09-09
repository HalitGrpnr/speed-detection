import { useState } from 'react'
import { Grid3x3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  pointCount: number
  onApply: (cols: number, rows: number, laneWidth: number, rowSpacing: number) => void
}

/**
 * Grid preset: noktalara satır-bazlı (row-major) dünya koordinatı atar.
 * i. nokta → X = (i % cols) * laneWidth, Y = floor(i / cols) * rowSpacing.
 */
export function GridPresetBar({ pointCount, onApply }: Props) {
  const [cols, setCols] = useState(2)
  const [rows, setRows] = useState(2)
  const [laneWidth, setLaneWidth] = useState(3.5)
  const [rowSpacing, setRowSpacing] = useState(5)

  const needed = cols * rows
  const hint =
    pointCount === 0
      ? `Önce canvas'a ${needed} nokta işaretleyin, sonra Grid Uygula'ya basın.`
      : pointCount < needed
        ? `${cols}×${rows} = ${needed} nokta gerekli, ${pointCount} var — mevcut noktalar atanır.`
        : `İlk ${needed} nokta grid koordinatlarıyla güncellenir.`

  return (
    <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Grid3x3 className="size-4 text-muted-foreground" /> Grid Preset
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-muted-foreground">
          Sütun
          <select
            value={cols}
            onChange={(e) => setCols(Number(e.target.value))}
            className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm"
          >
            {[2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted-foreground">
          Satır
          <select
            value={rows}
            onChange={(e) => setRows(Number(e.target.value))}
            className="mt-1 w-full rounded border border-input bg-background px-2 py-1 text-sm"
          >
            {[2, 3, 4].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted-foreground">
          Şerit gen. (m)
          <Input
            type="number"
            step="0.1"
            min="0.5"
            value={laneWidth}
            onChange={(e) => setLaneWidth(Number(e.target.value))}
            className="mt-1 h-8"
          />
        </label>
        <label className="text-xs text-muted-foreground">
          Satır aralığı (m)
          <Input
            type="number"
            step="0.5"
            min="0.5"
            value={rowSpacing}
            onChange={(e) => setRowSpacing(Number(e.target.value))}
            className="mt-1 h-8"
          />
        </label>
      </div>
      <p className="text-[0.7rem] text-muted-foreground">{hint}</p>
      <Button
        variant="secondary"
        size="sm"
        className="w-full"
        disabled={pointCount === 0}
        onClick={() => onApply(cols, rows, laneWidth, rowSpacing)}
      >
        Grid Uygula
      </Button>
    </div>
  )
}
