import { AlertCircle, Check, Lock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { STEPS, useWizard, type StepId } from '@/store/wizard'
import { useCrossRatio, XR_STEPS } from '@/features/crossratio/store'

export function Stepper() {
  const flow = useWizard((s) => s.flow)
  const legacyStep = useWizard((s) => s.step)
  const legacyGoTo = useWizard((s) => s.goTo)
  const legacyCanEnter = useWizard((s) => s.canEnter)
  const setFlow = useWizard((s) => s.setFlow)
  const calibration = useWizard((s) => s.calibration)
  // Tüm xr durumuna abone ol: adım kilitleri (canEnter) her girdi değişiminde yeniden hesaplanır
  const xrState = useCrossRatio()
  const { step: xrStep, goTo: xrGoTo, canEnter: xrCanEnter } = xrState

  const xr = flow === 'crossratio'
  const steps = xr ? XR_STEPS : STEPS
  const step = xr ? xrStep : legacyStep
  const goTo = (id: StepId) => (xr ? xrGoTo(id) : legacyGoTo(id))
  const canEnter = (id: StepId) => (xr ? xrCanEnter(id) : legacyCanEnter(id))

  const stepWarnings: Partial<Record<StepId, boolean>> = xr ? {} : {
    4: calibration != null && (
      calibration.rms_m * 100 > 5 ||
      !!calibration.planarity_warning ||
      calibration.point_count < 6
    ),
  }

  return (
    <nav className="flex flex-col gap-1 p-3">
      <div className="px-3 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
        {xr ? 'Ölçüm Sihirbazı' : 'Kalibrasyon Sihirbazı'}
      </div>
      {steps.map((s) => {
        const id = s.id as StepId
        const active = id === step
        const done = id < step
        const enabled = canEnter(id)
        const hasWarning = done && !!stepWarnings[id]

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
                done && !hasWarning && 'border-success bg-success text-success-foreground',
                done && hasWarning && 'border-warning bg-warning text-warning-foreground',
                !active && !done && 'border-muted-foreground/30',
              )}
            >
              {done
                ? hasWarning
                  ? <AlertCircle className="size-3.5" />
                  : <Check className="size-3.5" />
                : !enabled
                  ? <Lock className="size-3" />
                  : id}
            </span>
            {s.label}
          </button>
        )
      })}
      {xr && (
        <button type="button" onClick={() => setFlow('legacy')}
          className="mt-3 rounded-lg px-3 py-2 text-left text-xs text-muted-foreground hover:bg-accent hover:text-foreground">
          ← Video ve yöntem seçimine dön
        </button>
      )}
    </nav>
  )
}
