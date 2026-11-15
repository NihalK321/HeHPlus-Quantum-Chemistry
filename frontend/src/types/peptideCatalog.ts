/**
 * Types for the read-only, deduplicated catalog endpoint.  These records are
 * normalized by the backend from the original sequence library and the
 * additive catalog; the browser never infers chemical identity or provenance.
 */

import type { SelectedPeptideCandidate } from './peptideLibrary'

export interface CatalogFeatureCoordinates {
  start: number
  end: number
  coordinateSystem?: string | null
}

export interface CatalogAnnotation {
  type?: string
  description?: string
  [key: string]: unknown
}

export interface CatalogSourceReference {
  id: string
  sourceDatabase: string
  sourceAccession: string
  sourceRecordKey: string | null
  sourceUrl: string | null
  parentProteinAccession: string | null
  peptideFeatureCoordinates: CatalogFeatureCoordinates | null
  description: string | null
  annotations: CatalogAnnotation[]
  modifications: CatalogAnnotation[]
  catalogs: string[]
}

export interface CatalogMolecularInformation {
  formula: string | null
  molecularWeightGmol: string | null
  smiles: string | null
  inchiKey: string | null
  chemblCanonicalSmiles?: string | null
}

export interface PeptideCatalogRecord {
  /** Stable, catalog-qualified identity supplied by the aggregate endpoint. */
  id: string
  name: string
  aliases: string[]
  kind: string
  sequence: string | null
  sequenceLength: number | null
  selectableForOptimization: boolean
  sequenceOnlyScoringEligible: boolean
  sequenceOnlyScoringExclusionReason: string | null
  nonstandardResidues: string[]
  sourceReferences: CatalogSourceReference[]
  catalogs: string[]
  catalogRecordIds: string[]
  molecularInformation: CatalogMolecularInformation | null
}

export interface PeptideCatalogSearchParams {
  search?: string
  source?: string
  minLength?: number
  maxLength?: number
  annotation?: string
  page?: number
  pageSize?: number
}

export interface PeptideCatalogSearchResponse {
  items: PeptideCatalogRecord[]
  page: number
  pageSize: number
  total: number
  totalPages?: number
}

export interface PeptideCatalogStats {
  deduplicatedCandidateCount: number
  sequenceCandidateCount: number
  modifiedCandidateCount: number
  rawCatalogRecordCount?: number
  originalCatalog?: {
    uniqueSequenceRecords: number
    sourceRecordCount: number
  }
  extraCatalog?: {
    rawRecordCount: number
  }
  bySource: Record<string, number>
}

/**
 * Convert only a validated, sequence-bearing aggregate record into the
 * existing future-QAOA hand-off shape. Modified compounds never pass this
 * boundary.
 */
export function toSelectedCatalogCandidate(record: PeptideCatalogRecord): SelectedPeptideCandidate {
  if (!record.selectableForOptimization || !record.sequenceOnlyScoringEligible || !record.sequence || record.sequenceLength === null) {
    throw new Error('This catalog record is not eligible for sequence-based candidate selection.')
  }

  const primarySource = record.sourceReferences[0]

  return {
    peptideId: record.id,
    name: record.name,
    sequence: record.sequence,
    sequenceLength: record.sequenceLength,
    sourceDatabase: primarySource?.sourceDatabase ?? 'Unavailable source',
    sourceAccession: primarySource?.sourceAccession ?? 'Unavailable accession',
    sourceUrl: primarySource?.sourceUrl ?? '',
    requiresSpecialHandling: false,
    nonstandardResidues: record.nonstandardResidues,
  }
}
