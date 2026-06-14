import { Button } from '@/components/ui/button'
import { useWizard } from '@/store/wizard'
import { StepPlaceholder } from '../_shared/StepPlaceholder'

export function UploadStep() {
  const setVideoMeta = useWizard((s) => s.setVideoMeta)

  return (
    <StepPlaceholder
      title="Adım 1 — Video Yükle"
      description="Trafik kazası videosunu yükleyin. Bütünlük için SHA-256 hesaplanır; orijinale yazılmaz."
      implStep="Step 2"
    >
      <Button
        variant="outline"
        size="sm"
        onClick={() =>
          setVideoMeta({
            video_id: 'demo',
            fps: 25,
            fps_source: 'container',
            width: 1920,
            height: 1080,
            frame_count: 500,
            sha256: '0'.repeat(64),
          })
        }
      >
        (geçici) Örnek video meta ile doldur
      </Button>
    </StepPlaceholder>
  )
}
