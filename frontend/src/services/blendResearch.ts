import { ApiClient } from '../api/client'

export interface ChemicalGoals {
  ph: number
  target_charge: number
  target_hydropathy: number
  charge_weight: number
  hydropathy_weight: number
  diversity_weight: number
}

export interface QaoaExecution {
  layers: number
  max_iterations: number
  shots: number
  seed: number
}

export const defaultQaoaExecution: QaoaExecution = { layers: 1, max_iterations: 60, shots: 2048, seed: 42 }

export interface BlendCandidate {
  id: string
  name: string
  sequence: string
  source: string
  accession: string
  source_url: string
  score?: number
  charge?: number
  hydropathy?: number
  mass_da?: number
}

export interface CatalogStats {
  imported_source_records: number
  unique_eligible_sequences: number
  excluded_modified_or_unsupported_records: number
  sources: string[]
}

export interface CatalogPage {
  items: BlendCandidate[]
  total: number
  page: number
  page_size: number
  catalog: CatalogStats
}

export interface ShortlistResult {
  candidates: BlendCandidate[]
  catalog: CatalogStats
  scored_count: number
  shortlist_method: string
}

export interface BlendSelection {
  bitstring: string
  candidates: BlendCandidate[]
  objective: number
  individual_score_sum: number
  weighted_redundancy_penalty: number
}

export interface BlendResult {
  contract_version: string
  provenance: 'simulated'
  status: 'completed' | 'no_feasible_sample'
  execution_backend: string
  goals: ChemicalGoals & QaoaExecution & { blend_size: number }
  experiment_id?: string
  candidates: BlendCandidate[]
  selected_blend: BlendSelection | null
  classical_reference: BlendSelection
  benchmark: {
    pool_size: number
    feasible_subset_count: number
    bitstring_count: number
    feasible_probability: number
    observed_feasibility_rate: number
    optimum_probability: number
    uniform_optimum_probability: number
    uniform_feasible_probability: number
    sampled_objective_gap: number | null
  }
  history: { evaluation: number; expected_penalized_objective: number; feasible_probability: number }[]
  converged: boolean
  optimizer_message: string
  evaluations: number
  shots: number
  elapsed_seconds: number
  circuit_depth: number
  circuit_qasm: string
  limitations: string[]
  scoring_method: Record<string, string>
  catalog: CatalogStats
  counts?: Record<string, number>
  parameters?: number[]
  qubo?: {
    constant: number
    linear: number[]
    quadratic_upper_triangle: number[][]
    matrix_upper_triangle?: number[][]
    cardinality_penalty: number
    pair_overlap_upper_triangle: number[][]
  }
  ising?: { offset: number; fields: number[]; couplings_upper_triangle: number[][] }
  validation?: { passed: boolean; checked_binary_states: number; checked_feasible_subsets: number }
  sampling?: { feasible_shots: number; infeasible_shots: number }
}

const client = new ApiClient()
const savedRunKey = 'pepperq.blend-research-v1.latest'

export const blendResearch = {
  catalog(search = '', page = 1, signal?: AbortSignal): Promise<CatalogPage> {
    return client.request(`blends/catalog?${new URLSearchParams({ search, page: String(page) })}`, { signal })
  },
  shortlist(goals: ChemicalGoals, search: string): Promise<ShortlistResult> {
    return client.request('blends/shortlist', { method: 'POST', body: { ...goals, search, pool_size: 8 } })
  },
  optimize(goals: ChemicalGoals, candidateIds: string[], blendSize: number, execution: QaoaExecution = defaultQaoaExecution): Promise<BlendResult> {
    return client.request('blends/optimize', {
      method: 'POST',
      body: { ...goals, candidate_ids: candidateIds, blend_size: blendSize, ...execution },
    })
  },
}

export function saveLatestBlend(result: BlendResult): boolean {
  try {
    localStorage.setItem(savedRunKey, JSON.stringify(result))
    return true
  } catch {
    return false
  }
}

export function loadLatestBlend(): BlendResult | null {
  try {
    const raw = localStorage.getItem(savedRunKey)
    if (!raw) return null
    const value = JSON.parse(raw) as BlendResult
    return value.contract_version === '1.0' && value.provenance === 'simulated' && Array.isArray(value.candidates) ? value : null
  } catch {
    return null
  }
}
