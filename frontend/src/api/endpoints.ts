/**
 * Proposed client-side route names. These are not an approved backend
 * contract; update them only after the FastAPI schema is agreed by the team.
 */
export const proposedEndpoints = {
  health: 'health',
  capabilities: 'capabilities',
  peptideAnalysis: 'peptides/analyze',
  optimizations: 'optimizations',
  optimization: (id: string) => `optimizations/${encodeURIComponent(id)}`,
  comparison: 'comparisons',
  tradeoffs: 'tradeoffs',
  noiseExperiments: 'noise/experiments',
} as const
