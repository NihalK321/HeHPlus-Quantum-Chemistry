/**
 * Shared domain concepts for the frontend. These types describe API-shaped
 * data only; they intentionally do not embed scientific fixture values.
 */

export type DataAvailability = 'available' | 'pending' | 'unavailable'

export type JobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'unavailable'

export type ExecutionTarget = 'simulator' | 'hardware' | 'classical'

export interface Provenance {
  source: string
  generatedAt?: string
  executionTarget?: ExecutionTarget
  simulator?: string
  mitigationMethod?: string
  notes?: string
}

export interface PeptideConstraints {
  minimumLength?: number
  maximumLength?: number
  excludedResidues?: string[]
  requiredMotifs?: string[]
  notes?: string
}

export interface PeptideDesignInput {
  sequence: string
  constraints?: PeptideConstraints
}

export interface ObjectiveWeight {
  key: string
  label: string
  weight: number
}

export interface QaoaConfiguration {
  reps: number
  shots?: number
  optimizer?: string
  seed?: number
  executionTarget: ExecutionTarget
}

export interface OptimizationRequest {
  peptide: PeptideDesignInput
  objectives: ObjectiveWeight[]
  qaoa: QaoaConfiguration
}

export interface OptimizationRunSummary {
  id: string
  status: JobStatus
  submittedAt: string
  updatedAt?: string
  label?: string
  provenance?: Provenance
}

export interface MeasuredProperty {
  key: string
  label: string
  value: number | string
  unit?: string
  availability: DataAvailability
}

export interface ChemistryAnalysisRequest {
  peptide: PeptideDesignInput
  pH?: number
}

export interface ChemistryAnalysisResult {
  availability: DataAvailability
  properties: MeasuredProperty[]
  provenance?: Provenance
}

export interface ComparisonSeries {
  method: string
  executionTarget: ExecutionTarget
  availability: DataAvailability
  values: Array<{ label: string; value: number }>
  provenance?: Provenance
}

export interface TradeoffPoint {
  id: string
  objectives: Record<string, number>
  availability: DataAvailability
  provenance?: Provenance
}

export interface NoiseExperimentRequest {
  optimizationRunId?: string
  noiseModel: string
  mitigationMethod?: string
  shots?: number
}

export interface NoiseExperimentSummary {
  id: string
  status: JobStatus
  submittedAt: string
  provenance?: Provenance
}
