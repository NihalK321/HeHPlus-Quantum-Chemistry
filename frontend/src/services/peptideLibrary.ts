import { ApiClient } from '../api/client'
import type { PeptideLibraryRecord, PeptideLibraryStats, PeptideSearchParams, PeptideSearchResponse } from '../types/peptideLibrary'

const peptideLibraryRoutes = {
  collection: 'peptides',
  detail: (peptideId: string) => `peptides/${encodeURIComponent(peptideId)}`,
  stats: 'peptides/stats',
} as const

function toQueryString(params: PeptideSearchParams): string {
  const query = new URLSearchParams()

  if (params.search?.trim()) query.set('search', params.search.trim())
  if (params.source?.trim()) query.set('source', params.source.trim())
  if (params.minLength !== undefined) query.set('min_length', String(params.minLength))
  if (params.maxLength !== undefined) query.set('max_length', String(params.maxLength))
  if (params.annotation?.trim()) query.set('annotation', params.annotation.trim())
  if (params.page !== undefined) query.set('page', String(params.page))
  if (params.pageSize !== undefined) query.set('page_size', String(params.pageSize))

  const serialized = query.toString()
  return serialized ? `?${serialized}` : ''
}

/**
 * Isolates the agreed peptide-library API from UI components. The service is
 * dormant until a page explicitly searches or loads a detail record.
 */
export class PeptideLibraryService {
  private readonly client: ApiClient

  constructor(client: ApiClient = new ApiClient()) {
    this.client = client
  }

  search(params: PeptideSearchParams = {}): Promise<PeptideSearchResponse> {
    return this.client.request<PeptideSearchResponse>(`${peptideLibraryRoutes.collection}${toQueryString(params)}`)
  }

  get(peptideId: string): Promise<PeptideLibraryRecord> {
    return this.client.request<PeptideLibraryRecord>(peptideLibraryRoutes.detail(peptideId))
  }

  stats(): Promise<PeptideLibraryStats> {
    return this.client.request<PeptideLibraryStats>(peptideLibraryRoutes.stats)
  }
}

export const peptideLibraryService = new PeptideLibraryService()
