import { ApiClient } from '../api/client'
import type { HehExperiment } from '../types/quantumChemistry'

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
