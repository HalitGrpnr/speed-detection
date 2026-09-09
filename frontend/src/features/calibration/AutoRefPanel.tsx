import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import type { ProposedPoint } from '@/lib/models'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBanner } from '@/components/common/StatusBanner'

interface Props {
  videoId: string
  frame: number
  onProposals: (points: ProposedPoint[]) => void
}

/** M6 otomatik kontrol noktası önerisi (şerit/kesik çizgi tespiti). */
export function AutoRefPanel({ videoId, frame, onProposals }: Props) {
  const [laneWidth, setLaneWidth] = useState(3.5)
  const [dashLength, setDashLength] = useState(3.0)
  const [dNear, setDNear] = useState(5.0)

  const mutation = useMutation({
    mutationFn: () =>
      api.autoref(videoId, {
        frame_n: frame,
        lane_width_m: laneWidth,
        dash_length_m: dashLength,
        d_near_m: dNear,
      }),
    onSuccess: (points) => onProposals(points),
  })

  return (
    <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Sparkles className="size-4 text-muted-foreground" /> M6 Otomatik Öneri
      </div>
      <div className="grid grid-cols-3 gap-2">
        <label className="text-xs text-muted-foreground">
          Şerit (m)
          <Input
            type="number"
            step="0.1"
            value={laneWidth}
            onChange={(e) => setLaneWidth(Number(e.target.value))}
            className="mt-1 h-8"
          />
        </label>
        <label className="text-xs text-muted-foreground">
          Kesik (m)
          <Input
            type="number"
            step="0.1"
            value={dashLength}
            onChange={(e) => setDashLength(Number(e.target.value))}
            className="mt-1 h-8"
          />
        </label>
        <label className="text-xs text-muted-foreground">
          Yakın (m)
          <Input
            type="number"
            step="0.5"
            value={dNear}
            onChange={(e) => setDNear(Number(e.target.value))}
            className="mt-1 h-8"
          />
        </label>
      </div>

      <Button
        variant="secondary"
        size="sm"
        className="w-full"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
        Otomatik Öner
      </Button>

      {mutation.isError && (
        <StatusBanner tone="error">{(mutation.error as Error).message}</StatusBanner>
      )}
      {mutation.isSuccess && mutation.data.length === 0 && (
        <StatusBanner tone="warning">
          Otomatik öneri bulunamadı — şerit tespit edilemedi veya görüntü sınırı dışına taştı.
          Elle işaretleyin.
        </StatusBanner>
      )}
      {mutation.isSuccess && mutation.data.length > 0 && (
        <p className="text-[0.7rem] text-amber-700">
          {mutation.data.length} öneri eklendi. ⚠ Y koordinatları tahminidir — tabloda düzeltip
          doğrulayın.
        </p>
      )}
    </div>
  )
}
