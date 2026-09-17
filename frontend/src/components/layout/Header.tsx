import { Gauge, ShieldCheck } from 'lucide-react'
import { STEPS, useWizard } from '@/store/wizard'

export function Header() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const step = useWizard((s) => s.step)
  const stepLabel = STEPS.find((s) => s.id === step)?.label

  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b bg-card/80 px-5 backdrop-blur-md">
      <div className="flex shrink-0 items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-blue-700 text-primary-foreground shadow-pop">
          <Gauge className="size-5" />
        </div>
        <span className="font-semibold tracking-tight">Araç Hız Tespit Sistemi</span>
      </div>

      <span className="ml-2 hidden shrink-0 items-center gap-1.5 rounded-full border border-success/30 bg-success/10 px-2.5 py-1 text-[11px] font-medium text-success sm:inline-flex">
        <span className="size-1.5 animate-pulse rounded-full bg-success" />
        Tamamen Yerel
      </span>

      <div className="flex flex-1 items-center justify-center">
        {stepLabel && (
          <span className="hidden text-sm text-muted-foreground md:inline-flex">
            <span className="font-medium text-foreground">Adım {step}</span>
            <span className="mx-1.5">/</span>
            {STEPS.length}
            <span className="mx-2 text-border">·</span>
            <span className="text-foreground">{stepLabel}</span>
          </span>
        )}
      </div>

      {videoMeta && (
        <span
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-success/30 bg-success/10 px-2.5 py-1 text-xs font-medium text-success"
          title={`Dosya bütünlüğü doğrulandı\n${videoMeta.width}×${videoMeta.height} · ${videoMeta.fps.toFixed(2)} fps\nSHA-256: ${videoMeta.sha256}`}
        >
          <ShieldCheck className="size-4" />
          Dosya doğrulandı
        </span>
      )}
    </header>
  )
}
