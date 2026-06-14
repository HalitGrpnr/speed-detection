import { Button } from '@/components/ui/button'
import { useWizard } from '@/store/wizard'
import { StepPlaceholder } from '../_shared/StepPlaceholder'

export function PipelineStep() {
  const setJobId = useWizard((s) => s.setJobId)

  return (
    <StepPlaceholder
      title="Adım 5 — Analiz Parametreleri ve Başlat"
      description="Model boyutu, kare adımı ve FPS seçilir; analiz arka planda çalışır, ilerleme izlenir."
      implStep="Step 6"
    >
      <Button variant="outline" size="sm" onClick={() => setJobId('demo-job')}>
        (geçici) Örnek iş oluştur
      </Button>
    </StepPlaceholder>
  )
}
