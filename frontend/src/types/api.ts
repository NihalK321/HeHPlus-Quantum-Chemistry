import type {
  ChemistryAnalysisRequest,
  ChemistryAnalysisResult,
  ComparisonSeries,
  NoiseExperimentRequest,
  NoiseExperimentSummary,
  OptimizationRequest,
  OptimizationRunSummary,
  TradeoffPoint,
} from './domain'

/** The preferred envelope for future versioned FastAPI responses. */
export interface ApiEnvelope<T> {
  data: T
  requestId?: string
}

export interface ApiErrorPayload {
  detail: string
  code?: string
  requestId?: string
}

export interface ServiceHealth {
  status: 'ok' | 'degraded' | 'unavailable'
  version?: string
}

export interface Capability {
  key: string
  label: string
  availability: 'available' | 'pending' | 'unavailable'
  detail?: string
}

export interface CapabilityResponse {
  capabilities: Capability[]
}

export type AnalyzePeptideRequest = ChemistryAnalysisRequest
export type AnalyzePeptideResponse = ChemistryAnalysisResult

export type SubmitOptimizationRequest = OptimizationRequest
export type SubmitOptimizationResponse = OptimizationRunSummary

export interface OptimizationDetailResponse extends OptimizationRunSummary {
  resultAvailability: 'available' | 'pending' | 'unavailable'
}

export interface ComparisonResponse {
  series: ComparisonSeries[]
}

export interface TradeoffResponse {
  points: TradeoffPoint[]
}

export type SubmitNoiseExperimentRequest = NoiseExperimentRequest
export type SubmitNoiseExperimentResponse = NoiseExperimentSummary
