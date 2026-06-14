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

export type ControlPointSource = ControlPoint['source']
export type ConfidenceLevel = 'high' | 'medium' | 'low'
export type ModelSize = PipelineRequest['model_size']
