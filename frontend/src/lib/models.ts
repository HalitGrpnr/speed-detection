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
export type WheelMarkSource = 'manual' | 'auto' | 'operator-confirmed'

export interface WheelMark {
  frame: number  // tam veya alt-kare (T14)
  pixel: [number, number]
  source?: WheelMarkSource  // T20: opsiyonel, varsayılan 'manual'
}

export interface WheelSpeedRequest {
  marks: WheelMark[]
}

// T20 — Otomatik temas noktası önerileri
export interface AutoMarkOut {
  frame: number
  pixel: [number, number]
  source: 'auto'
  confidence: number          // 0-1; kenar=0.5, bbox=0.2
  detection_method: string    // 'edge-bottom' | 'bbox-heuristic'
  note: string
}

export interface AutoContactPointsResponse {
  marks: AutoMarkOut[]
  track_id: number
  method_summary: string
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

// T22 — Otomatik kalibrasyon önerisi (vanishing-point)
export interface AutoCalibrateRequest {
  frame_n: number
  lane_width_m: number
}

export interface AutoCalibratePointOut {
  id: string
  pixel: [number, number]
  world_m: [number, number]
  source: 'auto-vanishing'
}

export interface AutoCalibrateResponse {
  vanishing_point: [number, number] | null
  left_line_pts: [[number, number], [number, number]] | null
  right_line_pts: [[number, number], [number, number]] | null
  proposed_points: AutoCalibratePointOut[]
  quality_gate_passed: boolean
  quality_reason: string
  estimated_rms_m: number | null
  warning: string | null
}
