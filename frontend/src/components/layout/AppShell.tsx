import { type ReactNode, useState } from 'react'
import { cn } from '@/lib/utils'
import { useWizard } from '@/store/wizard'
import { Header } from './Header'
import { Footer } from './Footer'
import { Stepper } from './Stepper'

function AnalysisStatusBar() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const cal = useWizard((s) => s.calibration)
  const jobId = useWizard((s) => s.jobId)
  const step = useWizard((s) => s.step)

  if (!videoMeta) return null

  const items: { label: string; value: string; ok: boolean }[] = []

  const name = videoMeta.sha256 ? videoMeta.sha256.slice(0, 6) + '…' : '—'
  items.push({ label: 'Video', value: name, ok: true })

  if (cal) {
    const rmsOk = cal.rms_m * 100 < 5
    items.push({
      label: 'Kalibrasyon',
      value: `RMS ${(cal.rms_m * 100).toFixed(1)} cm`,
      ok: rmsOk,
    })
  }

  if (jobId && step >= 6) {
    items.push({ label: 'Analiz', value: 'tamamlandı', ok: true })
  }

  return (
    <div className="flex h-8 shrink-0 items-center gap-0 border-b bg-muted/30 px-5 text-[11px]">
      {items.map((item, i) => (
        <span key={item.label} className="flex items-center gap-1.5">
          {i > 0 && <span className="mx-3 text-border">·</span>}
          <span className="text-muted-foreground">{item.label}:</span>
          <span className={cn('font-medium tabular-nums', item.ok ? 'text-foreground' : 'text-warning')}>
            {item.value}
          </span>
          <span className={item.ok ? 'text-success' : 'text-warning'}>
            {item.ok ? '✓' : '⚠'}
          </span>
        </span>
      ))}
    </div>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const step = useWizard((s) => s.step)
  const flow = useWizard((s) => s.flow)
  const wide = flow === 'crossratio' || step === 3 || step === 6
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen flex-col text-foreground">
      <Header onToggleSidebar={() => setSidebarOpen((v) => !v)} />
      <AnalysisStatusBar />
      <div className="flex flex-1 overflow-hidden">
        <aside
          className={cn(
            'hidden shrink-0 border-r bg-card/60 backdrop-blur-sm md:block overflow-hidden transition-all duration-200',
            sidebarOpen ? 'w-52' : 'w-0 border-r-0',
          )}
        >
          <Stepper />
        </aside>
        <main className="flex-1 overflow-auto">
          <div
            className={cn(
              'mx-auto w-full px-6 py-6',
              wide ? 'max-w-7xl' : 'max-w-4xl',
            )}
          >
            {children}
          </div>
        </main>
      </div>
      <Footer />
    </div>
  )
}
