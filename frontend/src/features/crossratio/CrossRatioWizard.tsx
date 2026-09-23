import { Button } from '@/components/ui/button'
import { useWizard } from '@/store/wizard'
import { ContactMarksStep } from './ContactMarksStep'
import { KnownLengthStep } from './KnownLengthStep'
import { ResultStep } from './ResultStep'
import { TrackingStep } from './TrackingStep'
import { VanishingStep } from './VanishingStep'
import { VehicleWindowStep } from './VehicleWindowStep'
import { useCrossRatio, XR_STEPS, type XrStepId } from './store'

/** T28 — Cross-ratio ölçüm sihirbazı: tek araç, düz bir doğru, H gerektirmez. */
export function CrossRatioWizard() {
  const step = useCrossRatio((s) => s.step)
  const back = useCrossRatio((s) => s.back)
  const next = useCrossRatio((s) => s.next)
  const nextId = Math.min(6, step + 1) as XrStepId
  // Fonksiyon referansı değil sonucun kendisine abone ol — durum değişince buton güncellensin
  const nextOk = useCrossRatio((s) => s.canEnter(nextId))
  const setFlow = useWizard((s) => s.setFlow)

  return (
    <div className="space-y-4">
      {step === 1 && <TrackingStep />}
      {step === 2 && <VehicleWindowStep />}
      {step === 3 && <VanishingStep />}
      {step === 4 && <KnownLengthStep />}
      {step === 5 && <ContactMarksStep />}
      {step === 6 && <ResultStep />}

      <div className="flex items-center justify-between border-t pt-4">
        <Button variant="secondary" onClick={() => (step === 1 ? setFlow('legacy') : back())}>
          ← {step === 1 ? 'Video seçimi' : 'Geri'}
        </Button>
        {step < 6 && (
          <div className="flex items-center gap-3">
            {!nextOk && (
              <span className="text-xs text-muted-foreground">Devam etmek için yukarıdaki kontrolleri tamamlayın.</span>
            )}
            <Button onClick={next} disabled={!nextOk}>
              {XR_STEPS[nextId - 1].label} →
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
