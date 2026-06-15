import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ControlPoint, ControlPointSource } from '@/lib/models'
import { Button } from '@/components/ui/button'

const SOURCE_DOT: Record<ControlPointSource, string> = {
  operator: 'bg-amber-500',
  auto: 'bg-blue-400',
  site_measurement: 'bg-emerald-400',
}

interface Props {
  points: ControlPoint[]
  selectedId: string | null
  onSelect: (id: string) => void
  onUpdateWorld: (id: string, axis: 0 | 1, value: number) => void
  onUpdateSource: (id: string, source: ControlPointSource) => void
  onDelete: (id: string) => void
}

export function PointsTable({
  points,
  selectedId,
  onSelect,
  onUpdateWorld,
  onUpdateSource,
  onDelete,
}: Props) {
  if (points.length === 0) {
    return (
      <p className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
        Henüz nokta yok. Canvas'a tıklayarak veya M6 otomatik öneriyle nokta ekleyin.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left font-medium">#</th>
            <th className="px-3 py-2 text-left font-medium">Piksel (u, v)</th>
            <th className="px-3 py-2 text-left font-medium">X (m)</th>
            <th className="px-3 py-2 text-left font-medium">Y (m)</th>
            <th className="px-3 py-2 text-left font-medium">Kaynak</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {points.map((pt, i) => {
            const selected = pt.id === selectedId
            return (
              <tr
                key={pt.id}
                onClick={() => onSelect(pt.id)}
                className={cn(
                  'cursor-pointer border-t transition-colors',
                  selected ? 'bg-primary/5' : 'hover:bg-muted/40',
                )}
              >
                <td className="px-3 py-1.5">
                  <span className="inline-flex items-center gap-2">
                    <span className={cn('size-2 rounded-full', SOURCE_DOT[pt.source])} />
                    {i + 1}
                  </span>
                </td>
                <td className="px-3 py-1.5 font-mono text-xs text-muted-foreground">
                  {pt.pixel[0].toFixed(0)}, {pt.pixel[1].toFixed(0)}
                </td>
                <td className="px-3 py-1.5">
                  <input
                    type="number"
                    step="0.1"
                    value={pt.world_m[0]}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => onUpdateWorld(pt.id, 0, Number(e.target.value))}
                    className="w-20 rounded border border-input bg-background px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </td>
                <td className="px-3 py-1.5">
                  <input
                    type="number"
                    step="0.1"
                    value={pt.world_m[1]}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => onUpdateWorld(pt.id, 1, Number(e.target.value))}
                    className="w-20 rounded border border-input bg-background px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </td>
                <td className="px-3 py-1.5">
                  <select
                    value={pt.source}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => onUpdateSource(pt.id, e.target.value as ControlPointSource)}
                    className="rounded border border-input bg-background px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="operator">operatör</option>
                    <option value="auto">otomatik</option>
                    <option value="site_measurement">saha ölçümü</option>
                  </select>
                </td>
                <td className="px-3 py-1.5 text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(pt.id)
                    }}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
