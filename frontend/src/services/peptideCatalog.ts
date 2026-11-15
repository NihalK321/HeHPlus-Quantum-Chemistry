import { ApiClient } from '../api/client'
import type { PeptideCatalogRecord, PeptideCatalogSearchParams, PeptideCatalogSearchResponse, PeptideCatalogStats } from '../types/peptideCatalog'

const peptideCatalogRoutes = {
  collection: 'peptide-catalog',
  detail: (catalogId: string) => `peptide-catalog/${encodeURIComponent(catalogId)}`,
  stats: 'peptide-catalog/stats',
} as const

function toQueryString(params: PeptideCatalogSearchParams): string {
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
 * Isolates the merged-catalog API contract. The backend, not the browser,
 * verifies exact-sequence overlap and combines source provenance.
 */
export class PeptideCatalogService {
  private readonly client: ApiClient

  constructor(client: ApiClient = new ApiClient()) {
    this.client = client
  }

  search(params: PeptideCatalogSearchParams = {}): Promise<PeptideCatalogSearchResponse> {
    return this.client.request<PeptideCatalogSearchResponse>(`${peptideCatalogRoutes.collection}${toQueryString(params)}`)
  }

  get(catalogId: string): Promise<PeptideCatalogRecord> {
    return this.client.request<PeptideCatalogRecord>(peptideCatalogRoutes.detail(catalogId))
  }

  stats(): Promise<PeptideCatalogStats> {
    return this.client.request<PeptideCatalogStats>(peptideCatalogRoutes.stats)
  }
}

export const peptideCatalogService = new PeptideCatalogService()
