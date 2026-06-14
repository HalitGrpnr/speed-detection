import { ShieldCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useWizard } from '@/store/wizard'

export function Header() {
  const videoMeta = useWizard((s) => s.videoMeta)

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-card px-5">
      <div className="flex items-center gap-2">
        <ShieldCheck className="size-5 text-primary" />
        <span className="font-semibold tracking-tight">Araç Hız Tespit Sistemi</span>
      </div>

      <Badge variant="outline" className="text-muted-foreground">
        <span className="size-1.5 rounded-full bg-emerald-500" />
        Tamamen Yerel
      </Badge>

      <div className="ml-auto flex items-center gap-4 text-xs text-muted-foreground">
        {videoMeta && (
          <>
            <span className="max-w-[14rem] truncate" title={videoMeta.video_id}>
              {videoMeta.width}×{videoMeta.height} · {videoMeta.fps.toFixed(2)} fps
            </span>
            <span className="font-mono" title={`SHA-256: ${videoMeta.sha256}`}>
              SHA-256 {videoMeta.sha256.slice(0, 12)}…
            </span>
          </>
        )}
      </div>
    </header>
  )
}
