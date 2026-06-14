import type { ReactNode } from 'react'
import { Header } from './Header'
import { Stepper } from './Stepper'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-56 shrink-0 border-r bg-card/40">
          <Stepper />
        </aside>
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-4xl p-6">{children}</div>
        </main>
      </div>
    </div>
  )
}
