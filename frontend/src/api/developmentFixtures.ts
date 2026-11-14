import type { CapabilityResponse, ServiceHealth } from '../types/api'
import type { OptimizationRunSummary } from '../types/domain'

/**
 * Frontend-only fixtures. They communicate integration state and deliberately
 * contain no chemistry calculations, QAOA measurements, or benchmark claims.
 */
export const developmentFixtureLabel = 'Illustrative frontend fixture — not experiment data'

export const developmentHealth: ServiceHealth = {
  status: 'unavailable',
}

export const developmentCapabilities: CapabilityResponse = {
  capabilities: [
    {
      key: 'api-integration',
      label: 'FastAPI integration',
      availability: 'pending',
      detail: 'Awaiting an agreed API contract.',
    },
  ],
}

export const developmentRecentRuns: OptimizationRunSummary[] = []
