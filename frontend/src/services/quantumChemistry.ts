import { ApiClient } from '../api/client'
import type { HehArtifactProvenance, HehExperiment } from '../types/quantumChemistry'

/**
 * Proposed client-side endpoints only. These are not an approved FastAPI
 * contract and must be reconciled with the quantum backend before live use.
 */
export const proposedQuantumChemistryEndpoints = {
  hehExperiment: (experimentId: string) =>
    `quantum-chemistry/heh-plus/experiments/${encodeURIComponent(experimentId)}`,
} as const

/**
 * A dormant adapter that keeps VQE result loading isolated from page
 * components. It makes no request unless `getHehExperiment` is invoked.
 */
export class QuantumChemistryService {
  private readonly client: ApiClient

  constructor(client: ApiClient = new ApiClient()) {
    this.client = client
  }

  getHehExperiment(experimentId: string): Promise<HehExperiment> {
    return this.client.request<HehExperiment>(proposedQuantumChemistryEndpoints.hehExperiment(experimentId))
  }
}

type VerifiedHehArtifact = {
  artifactVersion: number
  artifactType: string
  artifactProvenance: HehArtifactProvenance
  experiment: HehExperiment
}

const verifiedArtifactFile = 'heh-plus-vqe-verified-scan.json'
const verifiedCircuitDirectory = 'research-artifacts'

export const verifiedHehArtifactUrl = `${import.meta.env.BASE_URL}${verifiedCircuitDirectory}/${verifiedArtifactFile}`

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function bundledAssetUrl(fileName: string): string {
  return `${import.meta.env.BASE_URL}${verifiedCircuitDirectory}/${encodeURIComponent(fileName)}`
}

/**
 * Load the checked-in, read-only export of the verified local HeH+ scan.
 * The browser never reads ignored quantum-workspace files at runtime. A live
 * FastAPI experiment can continue to use QuantumChemistryService above once
 * an agreed backend contract exists.
 */
export async function loadVerifiedHehExperiment(signal?: AbortSignal): Promise<HehExperiment> {
  const response = await fetch(verifiedHehArtifactUrl, {
    headers: { accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(`Verified HeH+ artifact request failed with HTTP ${response.status}.`)
  }

  const payload: unknown = await response.json()
  if (!isRecord(payload) || payload.artifactVersion !== 1 || !isRecord(payload.experiment) || !isRecord(payload.artifactProvenance)) {
    throw new Error('Verified HeH+ artifact has an unsupported shape.')
  }

  const artifact = payload as VerifiedHehArtifact
  if (artifact.artifactType !== 'pepperq.verified_heh_plus_vqe_potential_energy_scan' || artifact.experiment.molecule !== 'HeH+') {
    throw new Error('Verified HeH+ artifact does not describe the expected experiment.')
  }

  const circuit = artifact.experiment.circuitMetadata
  return {
    ...artifact.experiment,
    artifactProvenance: artifact.artifactProvenance,
    circuitMetadata: circuit && circuit.imageUrl
      ? { ...circuit, imageUrl: bundledAssetUrl(circuit.imageUrl) }
      : circuit,
  }
}
