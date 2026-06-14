import { Button } from '@/components/ui/button'
import { useWizard } from '@/store/wizard'
import type { ControlPoint } from '@/lib/models'
import { StepPlaceholder } from '../_shared/StepPlaceholder'

const DEMO_POINTS: ControlPoint[] = [
  { id: 'cp1', pixel: [400, 800], world_m: [0, 0], source: 'operator', held_out: false },
  { id: 'cp2', pixel: [900, 800], world_m: [3.5, 0], source: 'operator', held_out: false },
  { id: 'cp3', pixel: [500, 500], world_m: [0, 10], source: 'operator', held_out: false },
  { id: 'cp4', pixel: [850, 500], world_m: [3.5, 10], source: 'operator', held_out: false },
]

export function CalibrationStep() {
  const setControlPoints = useWizard((s) => s.setControlPoints)

  return (
    <StepPlaceholder
      title="Adım 3 — Kontrol Noktaları"
      description="Koyu canvas üzerinde nokta tıklayın, gerçek dünya koordinatlarını girin; canlı RMS hesaplanır."
      implStep="Step 4"
    >
      <div className="flex h-40 items-center justify-center rounded-lg bg-canvas text-sm text-canvas-foreground/70">
        Koyu kalibrasyon canvas'ı burada olacak (Step 4)
      </div>
      <Button variant="outline" size="sm" onClick={() => setControlPoints(DEMO_POINTS)}>
        (geçici) 4 örnek nokta ekle
      </Button>
    </StepPlaceholder>
  )
}
