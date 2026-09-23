import { create } from 'zustand'
import type { CrossRatioSpeedResponse, CrossRatioVpResponse, TrackSummary } from '@/lib/models'
import type { Pt } from './geometry'

/** T28 — Cross-ratio operatör sihirbazı durumu. Her adım bir öncekinin çıktısına dayanır;
 * geriye dönüp girdi değişirse bağımlı sonuçlar temizlenir (eski sayı ekranda kalmaz). */

export const XR_STEPS = [
  { id: 1, label: 'Araç Takibi' },
  { id: 2, label: 'Araç ve Aralık' },
  { id: 3, label: 'Perspektif Referansı' },
  { id: 4, label: 'Bilinen Uzunluk' },
  { id: 5, label: 'Temas Noktaları' },
  { id: 6, label: 'Sonuç' },
] as const

export type XrStepId = 1 | 2 | 3 | 4 | 5 | 6
export type LengthKind = 'wheelbase' | 'scene'
export type WheelbasePreset = 'model' | 'type'
export type MarkSource = 'manual' | 'operator-confirmed' | 'auto'

export interface KnownLengthState {
  kind: LengthKind
  wheelbasePreset: WheelbasePreset
  lengthM: number
  sigmaM: number
  pointA: Pt | null     // dingil: arka teker teması · olay yeri: 1. işaret
  pointB: Pt | null     // dingil: ön teker teması  · olay yeri: 2. işaret
  frame: number | null
}

export const TYPE_WHEELBASE = { lengthM: 2.65, sigmaM: 0.15 }   // binek tip varsayılanı
export const MODEL_WHEELBASE_SIGMA = 0.01
export const SCENE_SIGMA = 0.02

const INITIAL_LENGTH: KnownLengthState = {
  kind: 'wheelbase',
  wheelbasePreset: 'type',
  lengthM: TYPE_WHEELBASE.lengthM,
  sigmaM: TYPE_WHEELBASE.sigmaM,
  pointA: null,
  pointB: null,
  frame: null,
}

interface XrState {
  step: XrStepId
  jobId: string | null
  tracks: TrackSummary[]
  trackId: number | null
  frameStart: number | null
  frameEnd: number | null
  currentFrame: number
  laneLines: Pt[][]
  laneDraft: Pt[]
  useTrajectory: boolean
  vpPreview: CrossRatioVpResponse | null
  vpPrimary: 'lane' | 'trajectory'
  length: KnownLengthState
  marks: Record<number, { pixel: Pt; source: MarkSource }>
  result: CrossRatioSpeedResponse | null

  canEnter: (s: XrStepId) => boolean
  goTo: (s: XrStepId) => void
  next: () => void
  back: () => void

  setJob: (jobId: string | null) => void
  setTracks: (t: TrackSummary[]) => void
  selectTrack: (id: number) => void
  setWindow: (start: number | null, end: number | null) => void
  setCurrentFrame: (n: number) => void
  addLanePoint: (p: Pt) => void
  removeLaneLine: (i: number) => void
  clearLanes: () => void
  setUseTrajectory: (v: boolean) => void
  setVpPreview: (v: CrossRatioVpResponse | null) => void
  setVpPrimary: (v: 'lane' | 'trajectory') => void
  setLength: (patch: Partial<KnownLengthState>) => void
  setMark: (frame: number, pixel: Pt, source?: MarkSource) => void
  removeMark: (frame: number) => void
  clearMarks: () => void
  setResult: (r: CrossRatioSpeedResponse | null) => void
  reset: () => void
}

const INITIAL = {
  step: 1 as XrStepId,
  jobId: null,
  tracks: [] as TrackSummary[],
  trackId: null,
  frameStart: null,
  frameEnd: null,
  currentFrame: 0,
  laneLines: [] as Pt[][],
  laneDraft: [] as Pt[],
  useTrajectory: true,
  vpPreview: null,
  vpPrimary: 'lane' as const,
  length: INITIAL_LENGTH,
  marks: {} as Record<number, { pixel: Pt; source: MarkSource }>,
  result: null,
}

/** Kullanılacak VP'nin önizlemede mevcut olup olmadığı. */
export function usableVp(v: CrossRatioVpResponse | null, primary: 'lane' | 'trajectory') {
  if (!v) return null
  const pref = primary === 'lane' ? v.lane ?? v.trajectory : v.trajectory ?? v.lane
  return pref ?? null
}

export const useCrossRatio = create<XrState>((set, get) => ({
  ...INITIAL,

  canEnter: (s) => {
    const st = get()
    const windowOk =
      st.trackId != null && st.frameStart != null && st.frameEnd != null && st.frameEnd > st.frameStart
    switch (s) {
      case 1: return true
      case 2: return st.jobId != null && st.tracks.length > 0
      case 3: return windowOk
      case 4: return windowOk && usableVp(st.vpPreview, st.vpPrimary) != null
      case 5: return get().canEnter(4) && st.length.pointA != null && st.length.pointB != null && st.length.lengthM > 0
      case 6: return get().canEnter(5) && Object.keys(st.marks).length >= 2
    }
  },
  goTo: (s) => { if (get().canEnter(s)) set({ step: s }) },
  next: () => get().goTo(Math.min(6, get().step + 1) as XrStepId),
  back: () => set({ step: Math.max(1, get().step - 1) as XrStepId }),

  setJob: (jobId) => set({ ...INITIAL, jobId }),
  setTracks: (tracks) => set({ tracks }),
  selectTrack: (id) => {
    if (get().trackId === id) return
    const t = get().tracks.find((x) => x.track_id === id)
    set({
      trackId: id,
      frameStart: t?.first_frame ?? null,
      frameEnd: t?.last_frame ?? null,
      currentFrame: t?.first_frame ?? 0,
      vpPreview: null, length: { ...get().length, pointA: null, pointB: null, frame: null },
      marks: {}, result: null,
    })
  },
  setWindow: (frameStart, frameEnd) =>
    set({ frameStart, frameEnd, vpPreview: null, marks: {}, result: null }),
  setCurrentFrame: (currentFrame) => set({ currentFrame }),
  addLanePoint: (p) => {
    const draft = [...get().laneDraft, p]
    if (draft.length === 2) set({ laneLines: [...get().laneLines, draft], laneDraft: [], vpPreview: null, result: null })
    else set({ laneDraft: draft })
  },
  removeLaneLine: (i) => set({ laneLines: get().laneLines.filter((_, k) => k !== i), vpPreview: null, result: null }),
  clearLanes: () => set({ laneLines: [], laneDraft: [], vpPreview: null, result: null }),
  setUseTrajectory: (useTrajectory) => set({ useTrajectory, vpPreview: null, result: null }),
  setVpPreview: (vpPreview) => set({ vpPreview, result: null }),
  setVpPrimary: (vpPrimary) => set({ vpPrimary, result: null }),
  setLength: (patch) => set({ length: { ...get().length, ...patch }, result: null }),
  setMark: (frame, pixel, source = 'manual') =>
    set({ marks: { ...get().marks, [frame]: { pixel, source } }, result: null }),
  removeMark: (frame) => {
    const m = { ...get().marks }
    delete m[frame]
    set({ marks: m, result: null })
  },
  clearMarks: () => set({ marks: {}, result: null }),
  setResult: (result) => set({ result }),
  reset: () => set({ ...INITIAL }),
}))
