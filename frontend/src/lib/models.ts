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

// T14 — Kalibrasyon noktası alt-kare enterpolasyonu
export interface InterpolatePointRequest {
  frame_n_px: [number, number]
  frame_n1_px: [number, number]
  target_px: [number, number]
  second_n_px?: [number, number] | null
  second_n1_px?: [number, number] | null
}

export interface InterpolatePointResponse {
  interpolated_px: [number, number]
  t: number
  second_interpolated_px?: [number, number] | null
}

// T16 — Operatör-tekerlek hız ölçümü
export interface WheelMark {
  frame: number  // tam veya alt-kare (T14)
  pixel: [number, number]
}

export interface WheelSpeedRequest {
  marks: WheelMark[]
}

export interface WheelSpeedResponse {
  value_kmh: number
  ci_kmh: number
  confidence_level: string
  mark_count: number
  residual_kmh: number
  warnings: string[]
}

// T19 — Çok-işaretli hız profili (fren/ivme analizi)
export interface ProfilePoint {
  t_s: number
  speed_kmh: number
  ci_kmh: number
  accel_ms2: number | null
}

export interface WheelSpeedProfileRequest {
  marks: WheelMark[]
  smoothing_window?: number
}

export interface WheelSpeedProfileResponse {
  summary_value_kmh: number
  summary_ci_kmh: number
  summary_confidence_level: string
  summary_mark_count: number
  summary_residual_kmh: number
  points: ProfilePoint[]
  raw_pairwise_kmh: number[]
  smoothing_window: number
  warnings: string[]
}
