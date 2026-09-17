import { create } from 'zustand'
import type { CalibrateResponse, ControlPoint, JobSummary, VideoMeta } from '@/lib/models'

export const STEPS = [
  { id: 1, label: 'Video Yükle' },
  { id: 2, label: 'Kare Seç' },
  { id: 3, label: 'Noktalar' },
  { id: 4, label: 'Kalibrasyon' },
  { id: 5, label: 'Analiz' },
  { id: 6, label: 'Sonuçlar' },
] as const

export type StepId = 1 | 2 | 3 | 4 | 5 | 6

interface WizardState {
  step: StepId
  videoMeta: VideoMeta | null
  selectedFrame: number
  controlPoints: ControlPoint[]
  calibration: CalibrateResponse | null
  jobId: string | null
  sourceJobId: string | null  // recalibrate ile oluşturulduysa orijinal job_id

  /** Bir adıma girmek için ön koşullar sağlanmış mı? (kara-kutu/atlama engeli) */
  canEnter: (step: StepId) => boolean
  goTo: (step: StepId) => void
  next: () => void
  back: () => void

  setVideoMeta: (m: VideoMeta) => void
  setSelectedFrame: (n: number) => void
  setControlPoints: (p: ControlPoint[]) => void
  setCalibration: (c: CalibrateResponse | null) => void
  setJobId: (id: string | null) => void
  setSourceJobId: (id: string | null) => void
  /** T24 — Geçmiş bir analizi yükleyip doğrudan Adım 6'ya geç. */
  loadHistoricalJob: (summary: JobSummary, controlPoints: ControlPoint[]) => void
  reset: () => void
}

const INITIAL = {
  step: 1 as StepId,
  videoMeta: null,
  selectedFrame: 0,
  controlPoints: [] as ControlPoint[],
  calibration: null,
  jobId: null,
  sourceJobId: null,
}

export const useWizard = create<WizardState>((set, get) => ({
  ...INITIAL,

  canEnter: (step) => {
    const s = get()
    switch (step) {
      case 1:
        return true
      case 2:
      case 3:
        return s.videoMeta != null
      case 4:
        return s.videoMeta != null && s.controlPoints.length >= 4
      case 5:
        return s.calibration != null
      case 6:
        return s.jobId != null
      default:
        return false
    }
  },

  goTo: (step) => {
    if (get().canEnter(step)) set({ step })
  },
  next: () => {
    const nextId = Math.min(6, get().step + 1) as StepId
    get().goTo(nextId)
  },
  back: () => set({ step: Math.max(1, get().step - 1) as StepId }),

  setVideoMeta: (videoMeta) => set({ videoMeta }),
  setSelectedFrame: (selectedFrame) => set({ selectedFrame }),
  setControlPoints: (controlPoints) => set({ controlPoints }),
  setCalibration: (calibration) => set({ calibration }),
  setJobId: (jobId) => set({ jobId }),
  setSourceJobId: (sourceJobId) => set({ sourceJobId }),

  loadHistoricalJob: (summary, controlPoints) => set({
    ...INITIAL,
    jobId: summary.job_id,
    sourceJobId: null,
    controlPoints,
    videoMeta: summary.video_id ? {
      video_id: summary.video_id,
      fps: summary.fps ?? 25,
      fps_source: 'container',
      width: summary.width ?? 0,
      height: summary.height ?? 0,
      frame_count: summary.frame_count ?? 0,
      sha256: '',
    } : null,
    step: 6,
  }),

  reset: () => set({ ...INITIAL }),
}))
