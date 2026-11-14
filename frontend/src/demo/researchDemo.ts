import type { BenchmarkDisplay, BlendCandidate, DescriptorDisplay, PairwiseProxyDisplay, ResearchProvenance } from '../types/research'

export const demoProvenance: ResearchProvenance = {
  kind: 'demo',
  label: 'DEMO UI fixture',
  detail: 'Illustrative interface data only. It is not measured chemistry, a Qiskit result, or evidence of peptide compatibility.',
  source: 'Frontend demonstration dataset',
}

export const demoCandidates: BlendCandidate[] = [
  { id: 'C-01', label: 'Candidate 01', sequence: 'ACDEFGHIK', origin: 'entered', selected: true },
  { id: 'C-02', label: 'Candidate 02', sequence: 'ACDEYGHIK', origin: 'position-variant', selected: false, substitution: { position: 5, from: 'F', to: 'Y' } },
  { id: 'C-03', label: 'Candidate 03', sequence: 'VNQHLSTR', origin: 'entered', selected: true },
  { id: 'C-04', label: 'Candidate 04', sequence: 'VNPQLSTR', origin: 'position-variant', selected: false, substitution: { position: 4, from: 'Q', to: 'H' } },
  { id: 'C-05', label: 'Candidate 05', sequence: 'GLYRKTMQ', origin: 'imported', selected: true },
  { id: 'C-06', label: 'Candidate 06', sequence: 'GLFRKTMQ', origin: 'position-variant', selected: false, substitution: { position: 3, from: 'Y', to: 'F' } },
  { id: 'C-07', label: 'Candidate 07', sequence: 'STNQWRAK', origin: 'imported', selected: false },
  { id: 'C-08', label: 'Candidate 08', sequence: 'MELKSTPQ', origin: 'entered', selected: false },
]

export const demoBlendConfiguration = {
  targetPh: '7.4',
  temperature: '25 °C',
  selectedCount: 3,
  candidateCount: 8,
  feasibleSubsets: 56,
  bitstrings: 256,
  propertyWeights: [
    { label: 'Charge target', value: 0.35 },
    { label: 'Hydropathy proxy', value: 0.35 },
    { label: 'Diversity proxy', value: 0.3 },
  ],
}

export const demoDescriptors: DescriptorDisplay[] = [
  {
    label: 'Molecular mass',
    value: '1.04',
    unit: 'kDa (demo)',
    method: 'Illustrative display only',
    conditions: 'No calculation performed',
    uncertainty: 'Unavailable',
    provenance: demoProvenance,
  },
  {
    label: 'Estimated charge',
    value: '+0.6',
    unit: 'a.u. (demo)',
    method: 'Illustrative display only',
    conditions: 'pH 7.4 shown as a UI setting only',
    uncertainty: 'Unavailable',
    provenance: demoProvenance,
  },
  {
    label: 'Hydropathy',
    value: '0.42',
    unit: 'a.u. (demo)',
    method: 'Scale pending chemistry agreement',
    conditions: 'No chemistry calculation performed',
    uncertainty: 'Unavailable',
    provenance: demoProvenance,
  },
  {
    label: 'Structure status',
    value: 'No structure',
    unit: '—',
    method: 'Awaiting supplied PDB/SDF',
    conditions: 'Viewer accepts local structure files only',
    uncertainty: 'Not applicable',
    provenance: { ...demoProvenance, kind: 'unavailable', label: 'Structure unavailable' },
  },
]

export const demoPairwiseProxies: PairwiseProxyDisplay[] = [
  { firstCandidateId: 'C-01', secondCandidateId: 'C-03', value: 0.18, label: 'Demo proxy index', limitation: 'Not a compatibility, binding, or synergy measurement.', provenance: demoProvenance },
  { firstCandidateId: 'C-01', secondCandidateId: 'C-05', value: 0.42, label: 'Demo proxy index', limitation: 'Not a compatibility, binding, or synergy measurement.', provenance: demoProvenance },
  { firstCandidateId: 'C-03', secondCandidateId: 'C-05', value: 0.27, label: 'Demo proxy index', limitation: 'Not a compatibility, binding, or synergy measurement.', provenance: demoProvenance },
]

export const demoConvergence = [
  { iteration: 0, objective: 1.0 },
  { iteration: 1, objective: 0.88 },
  { iteration: 2, objective: 0.79 },
  { iteration: 3, objective: 0.73 },
  { iteration: 4, objective: 0.69 },
  { iteration: 5, objective: 0.67 },
]

export const demoBenchmark: BenchmarkDisplay = {
  label: 'Display-only benchmark fixture',
  qaoaObjective: 0.67,
  exactObjective: 0.61,
  feasibilityRate: 0.83,
  optimalityGap: 0.06,
  qaoaRuntimeMs: 184,
  classicalRuntimeMs: 9,
  shots: 1024,
  seed: 17,
  provenance: demoProvenance,
}

export const demoTradeoffPoints = [
  { id: 'Blend A', charge: 0.28, hydropathy: 0.74, selected: false },
  { id: 'Blend B', charge: 0.41, hydropathy: 0.62, selected: true },
  { id: 'Blend C', charge: 0.57, hydropathy: 0.55, selected: false },
  { id: 'Blend D', charge: 0.69, hydropathy: 0.39, selected: false },
]

export const demoNoiseComparison = [
  { state: 'Ideal simulator', error: 0.08 },
  { state: 'Noisy simulation', error: 0.21 },
  { state: 'Mitigated simulation', error: 0.16 },
]
