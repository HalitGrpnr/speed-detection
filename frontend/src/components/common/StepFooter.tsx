import { Button } from '@/components/ui/button'
import { useWizard, type StepId } from '@/store/wizard'

/** Adım altı gezinme: Geri / Devam. Devam, sonraki adımın guard'ı sağlanınca aktif olur. */
export function StepFooter({ onNext, nextLabel = 'Devam →' }: { onNext?: () => void; nextLabel?: string }) {
  const step = useWizard((s) => s.step)
  const back = useWizard((s) => s.back)
  const next = useWizard((s) => s.next)
  const canEnter = useWizard((s) => s.canEnter)
  const nextId = (step + 1) as StepId

  return (
    <div className="mt-6 flex items-center justify-between">
      <Button variant="secondary" onClick={back} disabled={step === 1}>
        ← Geri
      </Button>
      {step < 6 && (
        <Button onClick={onNext ?? next} disabled={!canEnter(nextId)}>
          {nextLabel}
        </Button>
      )}
    </div>
  )
}
