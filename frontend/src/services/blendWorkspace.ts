/** Browser-local draft shared by Designer and Optimization; never a run result. */
import { defaultQaoaExecution } from './blendResearch'
import type { BlendCandidate, BlendResult, ChemicalGoals, QaoaExecution } from './blendResearch'

export interface BlendWorkspace {
  version: 1
  goals: ChemicalGoals
  pool: BlendCandidate[]
  blendSize: number
  execution: QaoaExecution
}

export const defaultChemicalGoals: ChemicalGoals = {
  ph: 7.4, target_charge: 0, target_hydropathy: 0,
  charge_weight: 0.5, hydropathy_weight: 0.5, diversity_weight: 0.3,
}

const draftKey = 'pepperq.blend-research-v1.workspace'
const listeners = new Set<() => void>()
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

function readDraft(): BlendWorkspace {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(draftKey) ?? 'null')
    if (isRecord(parsed) && parsed.version === 1 && isRecord(parsed.goals) && isRecord(parsed.execution)
      && Object.keys(defaultChemicalGoals).every((key) => finite((parsed.goals as Record<string, unknown>)[key]))
      && Object.keys(defaultQaoaExecution).every((key) => finite((parsed.execution as Record<string, unknown>)[key]))
      && finite(parsed.blendSize) && Array.isArray(parsed.pool) && parsed.pool.length <= 8
      && parsed.pool.every((row: unknown) => isRecord(row)
        && ['id', 'name', 'sequence', 'source', 'accession', 'source_url'].every((key) => typeof row[key] === 'string')
        && /^[ACDEFGHIKLMNPQRSTVWY]{2,60}$/.test(String(row.sequence)))
      && new Set(parsed.pool.map((row: { id: string }) => row.id)).size === parsed.pool.length) {
      return parsed as unknown as BlendWorkspace
    }
  } catch { /* Storage can be disabled or contain an obsolete draft. */ }
  return { version: 1, goals: { ...defaultChemicalGoals }, pool: [], blendSize: 3, execution: { ...defaultQaoaExecution } }
}

let snapshot = readDraft()
let persisted = true
export const getBlendWorkspace = () => snapshot
export const isWorkspacePersisted = () => persisted
export function subscribeBlendWorkspace(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
export function updateBlendWorkspace(update: (current: BlendWorkspace) => BlendWorkspace) {
  snapshot = update(snapshot)
  const execution = Object.fromEntries(Object.entries(snapshot.execution).map(([key, value]) =>
    [key, finite(value) ? value : defaultQaoaExecution[key as keyof QaoaExecution]]))
  try { localStorage.setItem(draftKey, JSON.stringify({ ...snapshot, execution })); persisted = true }
  catch { persisted = false }
  listeners.forEach((listener) => listener())
}

export function matchingBlendResult(result: BlendResult, draft: BlendWorkspace): boolean {
  return result.candidates.length === draft.pool.length
    && result.candidates.every((row, index) => row.id === draft.pool[index].id && row.sequence === draft.pool[index].sequence)
    && Object.entries(draft.goals).every(([key, value]) => result.goals[key as keyof ChemicalGoals] === value)
    && result.goals.blend_size === draft.blendSize
    && Object.entries(draft.execution).every(([key, value]) => result.goals[key as keyof QaoaExecution] === value)
}

export function validateBlendWorkspace(draft: BlendWorkspace, checkExecution = true): string | null {
  if (draft.pool.length < 2 || draft.pool.length > 8) return 'Choose 2–8 supported peptides in Peptide Designer first.'
  if (!Number.isInteger(draft.blendSize) || draft.blendSize < 1 || draft.blendSize >= draft.pool.length) return 'Select at least one peptide and fewer than the number of candidates in the pool.'
  const ranges: Record<keyof ChemicalGoals, [number, number]> = {
    ph: [2, 12], target_charge: [-20, 20], target_hydropathy: [-4.5, 4.5],
    charge_weight: [0, 1], hydropathy_weight: [0, 1], diversity_weight: [0, 2],
  }
  for (const [key, [min, max]] of Object.entries(ranges)) {
    const value = draft.goals[key as keyof ChemicalGoals]
    if (!finite(value) || value < min || value > max) return `Set ${key.replaceAll('_', ' ')} between ${min} and ${max} in Designer.`
  }
  if (draft.goals.charge_weight + draft.goals.hydropathy_weight <= 0) return 'Set at least one chemical-property weight above zero in Designer.'
  if (!checkExecution) return null
  const executionRanges: Record<keyof QaoaExecution, [number, number]> = { layers: [1, 2], max_iterations: [10, 120], shots: [128, 8192], seed: [0, 2147483647] }
  for (const [key, [min, max]] of Object.entries(executionRanges)) {
    const value = draft.execution[key as keyof QaoaExecution]
    if (!Number.isInteger(value) || value < min || value > max) return `Set ${key.replaceAll('_', ' ')} to an integer between ${min} and ${max}.`
  }
  return null
}
