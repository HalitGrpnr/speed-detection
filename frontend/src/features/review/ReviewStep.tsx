import { Button } from '@/components/ui/button'
import { useWizard } from '@/store/wizard'
import { StepPlaceholder } from '../_shared/StepPlaceholder'

export function ReviewStep() {
  const setCalibration = useWizard((s) => s.setCalibration)

  return (
    <StepPlaceholder
      title="Adım 4 — Kalibrasyon Sonucu"
      description="RMS, kullanılan nokta, güven katmanı, düzlemsellik ve LOO doğrulaması burada özetlenir."
      implStep="Step 5"
    >
      <Button
        variant="outline"
        size="sm"
        onClick={() =>
          setCalibration({
            rms_m: 0.032,
            inlier_count: 4,
            confidence_layer: 'standard_assumption',
            homography: [
              [1, 0, 0],
              [0, 1, 0],
              [0, 0, 1],
            ],
            planarity_warning: false,
            point_count: 4,
            loo_rms_m: null,
            holdout_rows: [],
          })
        }
      >
        (geçici) Örnek kalibrasyon sonucu
      </Button>
    </StepPlaceholder>
  )
}
