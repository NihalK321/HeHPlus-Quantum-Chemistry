/**
 * Existing and proposed client-side route names. Peptide-library routes map
 * to the local FastAPI contract under the configured `/api/v1` base URL.
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
  peptideLibrary: 'peptides',
  peptideLibraryRecord: (id: string) => `peptides/${encodeURIComponent(id)}`,
  peptideLibraryStats: 'peptides/stats',
} as const
