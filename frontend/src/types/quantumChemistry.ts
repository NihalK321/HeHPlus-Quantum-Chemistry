/**
 * Frontend contract for the HeH+ VQE research module.
 *
 * These types deliberately describe calculation outputs and provenance rather
 * than producing chemistry or energy values in the browser. The FastAPI
 * schema must be agreed with the quantum team before a live endpoint is used.
 */

export type HehCalculationStatus =
  | 'not_started'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'unavailable'

export type HehEnergyConvention =
  | 'electronic_energy'
  | 'total_molecular_energy'
  | 'not_specified'

export type HehNuclearRepulsionTreatment = 'included' | 'excluded' | 'not_specified'

export type HehProvenanceKind = 'calculated' | 'simulated' | 'hardware' | 'reference' | 'unavailable'

export interface HehCalculationProvenance {
  kind: HehProvenanceKind
  label: string
  detail: string
  source?: string
  generatedAt?: string
  softwareVersion?: string
  randomSeed?: number
}

export interface HehMethodConfiguration {
  basisSet: string | null
  fermionToQubitMapping: string | null
  ansatz: string | null
  classicalOptimizer: string | null
  classicalReferenceMethod: string | null
  estimator: string | null
  executionContext: string | null
  qubitCount: number | null
  variationalParameterCount: number | null
  circuitDepth: number | null
  optimizerIterations: number | null
}

export interface HehEnergyPoint {
  bondDistanceAngstrom: number
  vqeEnergyHartree: number | null
  referenceEnergyHartree: number | null
  absoluteErrorHartree: number | null
  relativeError: number | null
  vqeEnergyUncertaintyHartree: number | null
  notes?: string | null
  calculationStatus: HehCalculationStatus
  provenance: HehCalculationProvenance
}

export interface HehConvergencePoint {
  iteration: number
  estimatedEnergyHartree: number | null
  referenceEnergyHartree: number | null
}

export interface HehConvergenceHistory {
  bondDistanceAngstrom: number
  points: HehConvergencePoint[]
  provenance: HehCalculationProvenance
}

export interface HehCircuitMetadata {
  qubitCount: number | null
  depth: number | null
  gateCount: number | null
  diagramSvg: string | null
  imageUrl: string | null
  imageAlt: string | null
  imageCaption: string | null
  provenance: HehCalculationProvenance
}

/** Source hashes and software versions retained with a checked-in result export. */
export interface HehArtifactProvenance {
  calculationSource: {
    fileName: string
    sha256: string
    createdAtUtc: string
  }
  circuitImageSource?: {
    fileName: string
    sha256: string
    bondDistanceAngstrom: number
  }
  packageVersions: Record<string, string>
}

export interface HehExperiment {
  experimentId: string
  molecule: 'HeH+'
  molecularCharge: 1
  electronCount: 2
  calculationStatus: HehCalculationStatus
  energyConvention: HehEnergyConvention
  nuclearRepulsionTreatment: HehNuclearRepulsionTreatment
  energyUnit: 'hartree'
  distanceUnit: 'angstrom'
  method: HehMethodConfiguration
  /** Raw arrays preserve the natural backend representation of a PES. */
  bondDistancesAngstrom: number[]
  vqeEnergiesHartree: Array<number | null>
  referenceEnergiesHartree: Array<number | null>
  energyPoints: HehEnergyPoint[]
  convergenceHistory: HehConvergenceHistory[]
  circuitMetadata: HehCircuitMetadata | null
  provenance: HehCalculationProvenance
  artifactProvenance?: HehArtifactProvenance
}

export function createUnavailableHehExperiment(): HehExperiment {
  const unavailableProvenance: HehCalculationProvenance = {
    kind: 'unavailable',
    label: 'Calculation data unavailable',
    detail: 'No HeH+ VQE calculation has been supplied by the quantum backend.',
  }

  return {
    experimentId: 'unavailable',
    molecule: 'HeH+',
    molecularCharge: 1,
    electronCount: 2,
    calculationStatus: 'unavailable',
    energyConvention: 'not_specified',
    nuclearRepulsionTreatment: 'not_specified',
    energyUnit: 'hartree',
    distanceUnit: 'angstrom',
    method: {
      basisSet: null,
      fermionToQubitMapping: null,
      ansatz: null,
      classicalOptimizer: null,
      classicalReferenceMethod: null,
      estimator: null,
      executionContext: null,
      qubitCount: null,
      variationalParameterCount: null,
      circuitDepth: null,
      optimizerIterations: null,
    },
    bondDistancesAngstrom: [],
    vqeEnergiesHartree: [],
    referenceEnergiesHartree: [],
    energyPoints: [],
    convergenceHistory: [],
    circuitMetadata: null,
    provenance: unavailableProvenance,
  }
}

/** Preferred public names matching the chemical notation used in the UI. */
export type HeHExperiment = HehExperiment
export type HeHEnergyPoint = HehEnergyPoint
export type VqeConvergencePoint = HehConvergencePoint
