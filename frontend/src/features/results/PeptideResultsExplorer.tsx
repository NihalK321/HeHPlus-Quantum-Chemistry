import { useMemo, useState } from 'react'
import { ArrowDownToLine, ChevronRight, FlaskConical, Search, ShieldAlert } from 'lucide-react'
import { demoCandidates, demoPairwiseProxies, demoProvenance } from '../../demo/researchDemo'
import { Button, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { MockDataNotice } from '../shared/MockDataNotice'

const demoContribution = [0.31, 0.24, 0.19, 0.15, 0.12, 0.1, 0.08, 0.07]

export function PeptideResultsExplorer() {
  const [query, setQuery] = useState('')
  const [activeCandidateId, setActiveCandidateId] = useState('C-01')

  const candidates = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    if (!normalizedQuery) return demoCandidates
    return demoCandidates.filter((candidate) => `${candidate.id} ${candidate.label} ${candidate.sequence}`.toLowerCase().includes(normalizedQuery))
  }, [query])

  const activeCandidate = demoCandidates.find((candidate) => candidate.id === activeCandidateId) ?? demoCandidates[0]
  const selectedCandidates = demoCandidates.filter((candidate) => candidate.selected)

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Results workspace"
        title="Candidate blend explorer"
        description="Inspect a proposed blend, its candidate records, declared constraints, and the evidence boundary around every displayed value."
        action={<Button variant="secondary" disabled><ArrowDownToLine size={15} /> Export when backend data is available</Button>}
      />

      <MockDataNotice detail={demoProvenance.detail} />

      <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel className="p-5" aria-labelledby="blend-result-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Proposed display blend</p>
              <h2 id="blend-result-heading" className="mt-1 text-lg font-semibold text-[#172B3A]">Blend B · UI fixture</h2>
            </div>
            <StatusPill tone="demo">Not an optimized result</StatusPill>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {selectedCandidates.map((candidate, index) => (
              <article key={candidate.id} className="rounded-lg border border-[#DCE7EC] bg-[#FBFDFD] p-3">
                <p className="font-mono text-xs font-semibold text-teal-700">{candidate.id}</p>
                <p className="mt-2 font-mono text-xs tracking-[0.1em] text-[#36505C]">{candidate.sequence}</p>
                <p className="mt-2 text-xs text-[#718791]">Demo component weight: {demoContribution[index].toFixed(2)} a.u.</p>
              </article>
            ))}
          </div>
          <div className="mt-5 grid gap-3 border-t border-[#E5EEF0] pt-4 sm:grid-cols-3">
            <div><p className="text-xs font-medium text-[#6B818B]">Objective</p><p className="mt-1 text-sm font-semibold text-[#172B3A]">0.67 a.u. <span className="font-normal text-[#718791]">demo</span></p></div>
            <div><p className="text-xs font-medium text-[#6B818B]">Cardinality</p><p className="mt-1 text-sm font-semibold text-[#172B3A]">3 of 8 <span className="font-normal text-[#718791]">display state</span></p></div>
            <div><p className="text-xs font-medium text-[#6B818B]">Feasibility</p><p className="mt-1 text-sm font-semibold text-[#172B3A]">Unavailable <span className="font-normal text-[#718791]">awaiting backend</span></p></div>
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="limitations-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-amber-50 text-amber-700"><ShieldAlert size={18} /></span>
            <div>
              <p className="research-eyebrow">Interpretation boundary</p>
              <h2 id="limitations-heading" className="mt-1 text-lg font-semibold text-[#172B3A]">What this page does not establish</h2>
            </div>
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-6 text-[#5E747F]">
            <li>Demo component and proxy values are not chemistry calculations or experimentally verified compatibility.</li>
            <li>A selected blend requires documented scoring, constraint validation, and exact classical comparison before interpretation.</li>
            <li>Sequence similarity, charge, or hydropathy alone do not demonstrate binding, synergy, safety, or formulation stability.</li>
          </ul>
        </Panel>
      </section>

      <Panel className="p-5" aria-labelledby="candidate-registry-heading">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="research-eyebrow">Candidate registry</p>
            <h2 id="candidate-registry-heading" className="mt-1 text-lg font-semibold text-[#172B3A]">Candidate records used by the interface</h2>
            <p className="mt-1 text-xs text-[#718791]">These sequences and provenance labels are centralized UI fixtures, not a documented candidate dataset.</p>
          </div>
          <label className="relative block w-full sm:w-64">
            <span className="sr-only">Filter candidate records</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#78909A]" size={15} />
            <input className="research-input pl-9 text-sm" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter ID or sequence" />
          </label>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="research-table min-w-[48rem]">
            <thead><tr><th>Candidate</th><th>Sequence</th><th>Origin</th><th>Substitution record</th><th>Blend state</th><th aria-label="Inspect" /></tr></thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr key={candidate.id} className={candidate.id === activeCandidateId ? 'bg-[#F4FAF9]' : undefined}>
                  <td><p className="font-semibold text-[#27424E]">{candidate.id}</p><p className="mt-0.5 text-xs text-[#718791]">{candidate.label}</p></td>
                  <td className="font-mono text-xs tracking-[0.08em] text-[#36505C]">{candidate.sequence}</td>
                  <td className="capitalize">{candidate.origin.replace('-', ' ')}</td>
                  <td>{candidate.substitution ? `Position ${candidate.substitution.position}: ${candidate.substitution.from} → ${candidate.substitution.to}` : 'No display variant'}</td>
                  <td><StatusPill tone={candidate.selected ? 'teal' : 'slate'}>{candidate.selected ? 'Selected display blend' : 'Candidate pool'}</StatusPill></td>
                  <td className="text-right"><button className="inline-flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-800" type="button" onClick={() => setActiveCandidateId(candidate.id)}>Inspect <ChevronRight size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {candidates.length === 0 && <p className="mt-5 rounded-md bg-[#F8FBFB] p-4 text-sm text-[#5E747F]">No display fixture matches that filter.</p>}
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel className="p-5" aria-labelledby="candidate-detail-heading">
          <p className="research-eyebrow">Candidate detail</p>
          <h2 id="candidate-detail-heading" className="mt-1 text-lg font-semibold text-[#172B3A]">{activeCandidate.id} · {activeCandidate.label}</h2>
          <div className="mt-5 rounded-lg border border-[#DCE7EC] bg-[#FBFDFD] p-4">
            <p className="font-mono text-sm tracking-[0.12em] text-[#27424E]">{activeCandidate.sequence}</p>
            <p className="mt-3 text-xs leading-5 text-[#718791]">Origin: {activeCandidate.origin.replace('-', ' ')}. {activeCandidate.substitution ? `UI substitution record at position ${activeCandidate.substitution.position}: ${activeCandidate.substitution.from} to ${activeCandidate.substitution.to}.` : 'No UI substitution record.'}</p>
          </div>
          <div className="mt-5 flex items-start gap-3 text-sm text-[#5E747F]"><FlaskConical className="mt-0.5 shrink-0 text-teal-700" size={17} /><p>Chemical descriptors and structure provenance should populate here only after documented backend calculations are available.</p></div>
        </Panel>

        <Panel className="p-5" aria-labelledby="pairwise-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Pairwise terms</p>
              <h2 id="pairwise-heading" className="mt-1 text-lg font-semibold text-[#172B3A]">Illustrative proxy record</h2>
              <p className="mt-1 text-xs text-[#718791]">A proxy term is not a compatibility, binding, or synergy claim.</p>
            </div>
            <StatusPill tone="demo">DEMO</StatusPill>
          </div>
          <div className="mt-5 overflow-x-auto">
            <table className="research-table min-w-[38rem]">
              <thead><tr><th>Pair</th><th>Term</th><th>Display value</th><th>Limitation</th></tr></thead>
              <tbody>{demoPairwiseProxies.map((proxy) => <tr key={`${proxy.firstCandidateId}-${proxy.secondCandidateId}`}><td className="font-mono text-xs text-[#36505C]">{proxy.firstCandidateId} · {proxy.secondCandidateId}</td><td>{proxy.label}</td><td>{proxy.value.toFixed(2)} a.u.</td><td className="text-[#718791]">{proxy.limitation}</td></tr>)}</tbody>
            </table>
          </div>
        </Panel>
      </section>
    </div>
  )
}
