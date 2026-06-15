import { Check, Lock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { STEPS, useWizard, type StepId } from '@/store/wizard'

export function Stepper() {
  const step = useWizard((s) => s.step)
  const goTo = useWizard((s) => s.goTo)
  const canEnter = useWizard((s) => s.canEnter)

  return (
    <nav className="flex flex-col gap-1 p-3">
      <div className="px-3 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
        Kalibrasyon Sihirbazı
      </div>
      {STEPS.map((s) => {
        const id = s.id as StepId
        const active = id === step
        const done = id < step
        const enabled = canEnter(id)

        return (
          <button
            key={id}
            type="button"
            disabled={!enabled}
            onClick={() => goTo(id)}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
              active && 'bg-primary/10 font-medium text-primary',
              !active && enabled && 'text-foreground hover:bg-accent',
              !enabled && 'cursor-not-allowed text-muted-foreground/40',
            )}
          >
            <span
              className={cn(
                'flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
                active && 'border-primary bg-primary text-primary-foreground',
                done && 'border-emerald-500 bg-emerald-500 text-white',
                !active && !done && 'border-muted-foreground/30',
              )}
            >
              {done ? <Check className="size-3.5" /> : !enabled ? <Lock className="size-3" /> : id}
            </span>
            {s.label}
          </button>
        )
      })}
    </nav>
  )
}
