/**
 * API-shaped types for verified peptide-library records. These types do not
 * create chemistry properties in the browser; every scientific field comes
 * from an imported source record or remains unavailable.
 */

export interface PeptideFeatureCoordinates {
  start: number
  end: number
  coordinateSystem: string
}

export interface PeptideAnnotation {
  type?: string
  description?: string
  evidence?: Array<Record<string, unknown>>
  [key: string]: unknown
}

export interface PeptideStructureReference {
  identifier: string
  url: string
  source?: string
  method?: string | null
  [key: string]: unknown
}

export interface PeptideSourceReference {
  id: string
  sourceDatabase: string
  sourceAccession: string
  sourceUrl: string
  sourceRecordKey: string
  parentProteinAccession: string | null
  peptideFeatureCoordinates: PeptideFeatureCoordinates | null
  name: string | null
  organism: string | null
  description: string | null
  annotations: PeptideAnnotation[]
  modifications: PeptideAnnotation[]
  structureReferences: PeptideStructureReference[]
  availableExperimentalProperties: Record<string, unknown> | null
  evidenceType: string | null
  sourceVersion: string | null
  retrievalTimestamp: string | null
  importedAt: string
  updatedAt: string
}

export interface PeptideLibraryRecord {
  id: string
  name: string
  sequence: string
  sequenceLength: number
  selectableForOptimization: boolean
  nonstandardResidues: string[]
  sourceReferences: PeptideSourceReference[]
  importedAt: string
  updatedAt: string
}

export interface PeptideSearchParams {
  search?: string
  source?: string
  minLength?: number
  maxLength?: number
  annotation?: string
  page?: number
  pageSize?: number
}

export interface PeptideSearchResponse {
  items: PeptideLibraryRecord[]
  page: number
  pageSize: number
  total: number
}

export interface PeptideLibraryStats {
  totalPeptides: number
  totalSourceRecords: number
  bySource: Record<string, number>
  withStructures: number
  withExperimentalAnnotations: number
}

/**
 * The typed hand-off for a later QAOA workflow. It contains a validated
 * sequence and source provenance, but deliberately no scoring or QAOA fields.
 */
export interface SelectedPeptideCandidate {
  peptideId: string
  name: string
  sequence: string
  sequenceLength: number
  sourceDatabase: string
  sourceAccession: string
  sourceUrl: string
  requiresSpecialHandling: boolean
  nonstandardResidues: string[]
}

export function toSelectedPeptideCandidate(record: PeptideLibraryRecord): SelectedPeptideCandidate {
  const primarySource = record.sourceReferences[0]

  return {
    peptideId: record.id,
    name: record.name,
    sequence: record.sequence,
    sequenceLength: record.sequenceLength,
    sourceDatabase: primarySource?.sourceDatabase ?? 'Unavailable source',
    sourceAccession: primarySource?.sourceAccession ?? 'Unavailable accession',
    sourceUrl: primarySource?.sourceUrl ?? '',
    requiresSpecialHandling: !record.selectableForOptimization || record.nonstandardResidues.length > 0,
    nonstandardResidues: record.nonstandardResidues,
  }
}
