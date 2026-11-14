import { ApiClient } from '../api/client'

/** Existing FastAPI 0.2.0 /optimize contract; independent of blend/VQE APIs. */
export interface GeneratedStructure {
  sequence: string
  best_structure_pdb: string
  energy_model: string
  torsions: { name: string }[]
  best_configuration: {
    bitstring: string
    energy_kcal_mol: number
  }
}

const structureBaseUrl = (import.meta.env.VITE_STRUCTURE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000').replace(/\/+$/, '')
const client = new ApiClient(structureBaseUrl)

export async function generateMolecularStructure(sequence: string, signal: AbortSignal): Promise<GeneratedStructure> {
  // Each internal proline removes a phi rotation because its N-CA bond is in a ring.
  const availableTorsions = 2 * (sequence.length - 1) - [...sequence.slice(1)].filter((residue) => residue === 'P').length
  const result = await client.request<GeneratedStructure>('optimize', {
    method: 'POST',
    signal,
    body: { sequence, method: 'classical', torsion_count: Math.min(3, availableTorsions), seed: 42 },
  })

  if (result?.sequence !== sequence || typeof result.best_structure_pdb !== 'string'
    || !/^(ATOM  |HETATM)/m.test(result.best_structure_pdb)
    || typeof result.energy_model !== 'string'
    || !Array.isArray(result.torsions) || result.torsions.length === 0
    || typeof result.best_configuration?.bitstring !== 'string'
    || !Number.isFinite(result.best_configuration?.energy_kcal_mol)) {
    throw new Error('The structure service did not return a valid peptide PDB model.')
  }

  return result
}
