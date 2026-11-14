import { lazy, Suspense } from 'react'
import { FlaskConical, Info, Layers3, Link2, Sigma } from 'lucide-react'
import { Button, EmptyState, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { demoCandidates, demoDescriptors, demoPairwiseProxies, demoProvenance } from '../../demo/researchDemo'
import { MockDataNotice } from '../shared/MockDataNotice'

const MolecularStructureViewer = lazy(() =>
  import('./MolecularStructureViewer').then((module) => ({ default: module.MolecularStructureViewer })),
)

const focalCandidate = demoCandidates[1]
const selectedCandidateIds = demoCandidates.filter((candidate) => candidate.selected).map((candidate) => candidate.id)

export function MolecularChemistryAnalyzer() {
  return (
    <div className="space-y-6">
      <SectionHeading
        action={<StatusPill tone="amber">Chemistry service pending</StatusPill>}
        description="Inspect descriptors, structural provenance, and cautiously scoped pairwise proxies. This workspace separates supplied evidence from interface-only display data."
        eyebrow="Chemistry workspace"
        title="Molecular chemistry analysis"
      />

      <MockDataNotice detail="All numeric descriptor and proxy values on this screen are centralized DEMO UI fixtures. They are not calculated chemistry, measured structure, or evidence of peptide compatibility." />

      <div className="grid gap-5 xl:grid-cols-[0.82fr_1.18fr]">
        <Panel aria-labelledby="candidate-context-heading" className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Candidate context</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="candidate-context-heading">Sequence and substitution record</h2>
            </div>
            <StatusPill tone="demo">Demo record</StatusPill>
          </div>

          <div className="mt-5 rounded-lg border border-[#DCE7EC] bg-[#FBFDFD] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-[#6C818B]">Selected for inspection</p>
                <p className="mt-1 text-base font-semibold text-[#223E49]">{focalCandidate.label}</p>
              </div>
              <span className="rounded-md bg-teal-50 px-2 py-1 font-mono text-xs font-semibold text-teal-800">{focalCandidate.id}</span>
            </div>
            <p className="mt-5 font-mono text-base tracking-[0.12em] text-[#24515B]">{focalCandidate.sequence.split('').join(' ')}</p>
            {focalCandidate.substitution && (
              <div className="mt-4 flex items-start gap-2 rounded-md border border-[#D6E5E8] bg-white p-3">
                <Sigma className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" aria-hidden="true" />
                <p className="text-sm leading-5 text-[#46616B]">
                  Position {focalCandidate.substitution.position}: {focalCandidate.substitution.from} → {focalCandidate.substitution.to}. This is a candidate-generation record, not a structural or chemical prediction.
                </p>
              </div>
            )}
          </div>

          <dl className="mt-5 divide-y divide-[#E7EFF1] text-sm">
            <div className="flex justify-between gap-5 py-3">
              <dt className="text-[#6B818B]">Input origin</dt>
              <dd className="text-right font-medium capitalize text-[#27424E]">{focalCandidate.origin.replace('-', ' ')}</dd>
            </div>
            <div className="flex justify-between gap-5 py-3">
              <dt className="text-[#6B818B]">Conditions shown</dt>
              <dd className="text-right font-medium text-[#27424E]">pH 7.4 · 25 °C (demo settings)</dd>
            </div>
            <div className="flex justify-between gap-5 py-3">
              <dt className="text-[#6B818B]">Descriptor source</dt>
              <dd className="text-right font-medium text-[#27424E]">{demoProvenance.label}</dd>
            </div>
          </dl>

          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
            Chemistry methods, mass conventions, charge model, hydropathy scale, and uncertainty are awaiting the chemistry scoring contract.
          </div>
        </Panel>

        <Panel aria-labelledby="descriptor-heading" className="p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="research-eyebrow">Descriptor record</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="descriptor-heading">Documented display fields</h2>
              <p className="mt-1 text-sm text-[#667E88]">A production response must populate every method, unit, condition, source, and uncertainty field.</p>
            </div>
            <StatusPill tone="demo">Display-only</StatusPill>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="research-table min-w-[48rem]">
              <thead>
                <tr>
                  <th>Descriptor</th>
                  <th>Value</th>
                  <th>Method / conditions</th>
                  <th>Uncertainty</th>
                </tr>
              </thead>
              <tbody>
                {demoDescriptors.map((descriptor) => (
                  <tr key={descriptor.label}>
                    <td>
                      <p className="font-semibold text-[#27424E]">{descriptor.label}</p>
                      <p className="mt-1 text-xs text-[#70858E]">{descriptor.provenance.label}</p>
                    </td>
                    <td>
                      <p className="font-semibold text-[#173B46]">{descriptor.value}</p>
                      <p className="mt-1 text-xs text-[#70858E]">{descriptor.unit}</p>
                    </td>
                    <td>
                      <p className="text-[#405B66]">{descriptor.method}</p>
                      <p className="mt-1 text-xs leading-5 text-[#70858E]">{descriptor.conditions}</p>
                    </td>
                    <td className="text-[#566E78]">{descriptor.uncertainty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <Panel aria-labelledby="structure-heading" className="p-5">
        <div className="flex flex-col gap-3 border-b border-[#DCE7EC] pb-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <Layers3 className="mt-0.5 h-5 w-5 text-teal-700" aria-hidden="true" />
            <div>
              <p className="research-eyebrow">Optional structural analysis</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="structure-heading">Supplied molecular structure</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-[#667E88]">Use a research-approved structure file only. A visual conformer is a hypothesis and does not establish folding, docking, blend stability, or compatibility.</p>
            </div>
          </div>
          <StatusPill tone="slate">Local-file viewer</StatusPill>
        </div>

        <Suspense fallback={<div className="mt-5"><EmptyState detail="Preparing the optional 3Dmol viewer…" title="Loading molecular visualization tools" /></div>}>
          <div className="mt-5">
            <MolecularStructureViewer />
          </div>
        </Suspense>

        <div className="mt-4 flex items-start gap-2 rounded-md border border-[#DCE7EC] bg-[#FBFDFD] p-3 text-sm leading-6 text-[#596F79]">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#52717B]" aria-hidden="true" />
          Residue substitution highlighting requires an agreed sequence-to-structure mapping. PepperQ does not infer that mapping from a file name or a sequence preview.
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel aria-labelledby="proxy-heading" className="p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="research-eyebrow">Pairwise terms</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="proxy-heading">Pairwise proxy registry</h2>
              <p className="mt-1 text-sm leading-6 text-[#667E88]">A future QUBO may use defensible pairwise penalties or proxies. These display values are not peptide compatibility evidence.</p>
            </div>
            <StatusPill tone="demo">Demo proxy</StatusPill>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="research-table min-w-[40rem]">
              <thead>
                <tr>
                  <th>Candidate pair</th>
                  <th>Term</th>
                  <th>Value</th>
                  <th>Limitation</th>
                </tr>
              </thead>
              <tbody>
                {demoPairwiseProxies.map((proxy) => (
                  <tr key={`${proxy.firstCandidateId}-${proxy.secondCandidateId}`}>
                    <td className="font-mono text-xs text-[#27424E]">{proxy.firstCandidateId} × {proxy.secondCandidateId}</td>
                    <td>{proxy.label}</td>
                    <td className="font-semibold text-[#27424E]">{proxy.value.toFixed(2)} <span className="font-normal text-[#718791]">a.u.</span></td>
                    <td className="max-w-xs leading-5 text-[#647B85]">{proxy.limitation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel aria-labelledby="blend-context-heading" className="p-5">
          <div className="flex items-start gap-3">
            <Link2 className="mt-0.5 h-5 w-5 text-teal-700" aria-hidden="true" />
            <div>
              <p className="research-eyebrow">Blend context</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="blend-context-heading">Selected whole candidates</h2>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {demoCandidates.filter((candidate) => selectedCandidateIds.includes(candidate.id)).map((candidate) => (
              <div className="rounded-md border border-[#DCE7EC] bg-[#FBFDFD] p-3" key={candidate.id}>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[#27424E]">{candidate.label}</p>
                  <span className="font-mono text-xs text-[#087E78]">{candidate.id}</span>
                </div>
                <p className="mt-2 font-mono text-xs tracking-[0.1em] text-[#5B737D]">{candidate.sequence.split('').join(' ')}</p>
              </div>
            ))}
          </div>
          <p className="mt-5 text-sm leading-6 text-[#617983]">QAOA will ultimately select whole candidate IDs for a blend. It does not select individual amino acids or establish molecular interaction mechanisms.</p>
          <Button className="mt-4" disabled variant="secondary">
            <FlaskConical className="h-4 w-4" aria-hidden="true" />
            Await chemistry calculation service
          </Button>
        </Panel>
      </div>
    </div>
  )
}
