import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { useWizard } from '@/store/wizard'
import { UploadStep } from '@/features/upload/UploadStep'
import { FrameStep } from '@/features/frame/FrameStep'
import { CalibrationStep } from '@/features/calibration/CalibrationStep'
import { ReviewStep } from '@/features/review/ReviewStep'
import { PipelineStep } from '@/features/pipeline/PipelineStep'
import { ResultsStep } from '@/features/results/ResultsStep'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

function CurrentStep() {
  const step = useWizard((s) => s.step)
  switch (step) {
    case 1:
      return <UploadStep />
    case 2:
      return <FrameStep />
    case 3:
      return <CalibrationStep />
    case 4:
      return <ReviewStep />
    case 5:
      return <PipelineStep />
    case 6:
      return <ResultsStep />
    default:
      return null
  }
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell>
        <CurrentStep />
      </AppShell>
    </QueryClientProvider>
  )
}

export default App
