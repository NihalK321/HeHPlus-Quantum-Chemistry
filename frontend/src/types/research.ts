export type ResearchDataKind = 'demo' | 'calculated' | 'simulated' | 'hardware' | 'unavailable'

export interface ResearchProvenance {
  kind: ResearchDataKind
  label: string
  detail: string
  source?: string
  method?: string
  updatedAt?: string
}

export interface BlendCandidate {
  id: string
  label: string
  sequence: string
  origin: 'entered' | 'position-variant' | 'imported'
  selected: boolean
  substitution?: {
    position: number
    from: string
    to: string
  }
}

export interface DescriptorDisplay {
  label: string
  value: string
  unit: string
  method: string
  conditions: string
  uncertainty: string
  provenance: ResearchProvenance
}

export interface PairwiseProxyDisplay {
  firstCandidateId: string
  secondCandidateId: string
  value: number
  label: string
  limitation: string
  provenance: ResearchProvenance
}

export interface BenchmarkDisplay {
  label: string
  qaoaObjective: number
  exactObjective: number
  feasibilityRate: number
  optimalityGap: number
  qaoaRuntimeMs: number
  classicalRuntimeMs: number
  shots: number
  seed: number
  provenance: ResearchProvenance
}
