/**
 * Backend (FastAPI/Pydantic) şemalarından üretilen tipler için okunabilir alias'lar.
 * Kaynak: src/lib/types.ts (openapi-typescript ile /openapi.json'dan üretilir — elle düzenleme).
 */
import type { components } from './types'

type Schemas = components['schemas']

export type VideoMeta = Schemas['VideoMetaOut']
export type ControlPoint = Schemas['ControlPointIn']
export type CalibrateRequest = Schemas['CalibrateRequest']
export type CalibrateResponse = Schemas['CalibrateResponse']
export type AutoRefRequest = Schemas['AutoRefRequest']
export type ProposedPoint = Schemas['ProposedPointOut']
export type PipelineRequest = Schemas['PipelineRequest']
export type JobStatus = Schemas['JobStatusOut']
export type SpeedEstimate = Schemas['SpeedEstimateOut']
export type JobResult = Schemas['JobResultOut']
export type AxleSuggestFrameResponse = Schemas['AxleSuggestFrameResponse']
export type AxleCheckRequest = Schemas['AxleCheckRequest']
export type AxleCheckResponse = Schemas['AxleCheckResponse']
export type PlanViewRequest = Schemas['PlanViewRequest']
export type RecalibrateRequest = Schemas['RecalibrateRequest']

export type ControlPointSource = ControlPoint['source']
export type ConfidenceLevel = 'high' | 'medium' | 'low'
export type ModelSize = PipelineRequest['model_size']

// T13 — Hız zaman serisi sparkline
export interface SpeedSeriesPoint {
  t_s: number
  speed_kmh: number
}

export interface SpeedSeriesOut {
  track_id: number
  points: SpeedSeriesPoint[]
  max_kmh: number
  median_kmh: number
}

// T8 — Dingil adımlama (types.ts'de yok, doğrudan tanımlanıyor)
export interface AxleStepRequest {
  frame_n: number
  front_pixel: [number, number]
  rear_pixel: [number, number]
  wheelbase_m: number
}

export interface AxleStepOut {
  frame: number
  distance_m: number
}

export interface AxleStepResponse {
  speed_kmh: number | null
  ci_kmh: number | null
  step_count: number
  steps: AxleStepOut[]
  interrupted: boolean
  interrupt_reason: string | null
  initial_distance_m: number | null  // manuel modda ön-arka mesafesi; otomatik modda null
  h_speed_window_kmh: number | null
}

export interface AxleStepAutoRequest {
  wheelbase_m: number
}
