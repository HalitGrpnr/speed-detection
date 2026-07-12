import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Map } from 'lucide-react'
import { api } from '@/lib/api'
import type { ControlPoint } from '@/lib/models'
import { InfoHint } from '@/components/common/InfoHint'
import { StatusBanner } from '@/components/common/StatusBanner'

interface Props {
  videoId: string
  frame: number
  controlPoints: ControlPoint[]
}

/**
 * M9 — kuş bakışı (kalibre edilmiş yol düzleminin projeksiyonu). DTP karşılaştırması §5.
 * Operatörün "bu düzlem doğru mu?" sorusunu görsel olarak yanıtlar; kontrol noktaları
 * değiştikçe otomatik yenilenir.
 */
export function PlanViewPreview({ videoId, frame, controlPoints }: Props) {
  const [imgUrl, setImgUrl] = useState<string | null>(null)

  const query = useQuery({
    queryKey: ['planView', videoId, frame, controlPoints],
    queryFn: () => api.planView(videoId, { frame_n: frame, control_points: controlPoints }),
    enabled: controlPoints.length >= 4,
  })

  useEffect(() => {
    if (!query.data) return
    const url = URL.createObjectURL(query.data)
    setImgUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [query.data])

  if (controlPoints.length < 4) return null

  return (
    <div className="space-y-2">
      <p className="flex items-center gap-1.5 text-sm font-medium">
        <Map className="size-4 text-muted-foreground" /> Kuş Bakışı Önizleme
        <InfoHint text="Kalibre ettiğiniz yol düzleminin tepeden projeksiyonu — gerçek bir görüntü değildir. Yalnızca kontrol noktalarının kapladığı bölge güvenilirdir; ince gri çizgiler 1 metre aralıklıdır. (Teknik: homografinin dünya düzlemine warp'ı)" />
      </p>

      {query.isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Önizleme hazırlanıyor…
        </div>
      )}

      {query.isError && (
        <StatusBanner tone="error">{(query.error as Error).message}</StatusBanner>
      )}

      {imgUrl && (
        <img
          src={imgUrl}
          alt="Kalibre edilmiş yol düzleminin kuş bakışı projeksiyonu"
          className="max-h-[420px] w-auto rounded-lg border bg-canvas shadow-card"
        />
      )}
    </div>
  )
}
