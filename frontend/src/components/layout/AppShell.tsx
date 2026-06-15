import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { useWizard } from '@/store/wizard'
import { Header } from './Header'
import { Footer } from './Footer'
import { Stepper } from './Stepper'

export function AppShell({ children }: { children: ReactNode }) {
  const step = useWizard((s) => s.step)
  // Kalibrasyon (3) tuval için en geniş alanı ister; diğer adımlar okunaklı dar kolon.
  const wide = step === 3 || step === 6

  return (
    <div className="flex h-screen flex-col text-foreground">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden w-60 shrink-0 border-r bg-card/60 backdrop-blur-sm md:block">
          <Stepper />
        </aside>
        <main className="flex-1 overflow-auto">
          <div
            className={cn(
              'mx-auto w-full px-6 py-7',
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
