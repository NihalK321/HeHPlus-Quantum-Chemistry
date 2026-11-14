import { useState } from 'react'
import { Activity, Cpu, Database, Play, ShieldCheck } from 'lucide-react'
import { demoBlendConfiguration, demoCandidates } from '../../demo/researchDemo'
import { Button, MetricCard, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { MockDataNotice } from '../shared/MockDataNotice'
import { QaoaConvergenceChart } from './QaoaConvergenceChart'
import { QuboObjectivePanel } from './QuboObjectivePanel'

export function QuantumOptimizationEngine() {
  const [layers, setLayers] = useState('2')
  const [shots, setShots] = useState('1024')
  const [executionTarget, setExecutionTarget] = useState('simulator')
  const [gamma, setGamma] = useState(0.5)
  const [lambda, setLambda] = useState(2)
  const [reviewStatus, setReviewStatus] = useState('No configuration has been sent to an optimization service.')

  const selectedCandidates = demoCandidates.filter((candidate) => candidate.selected)

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Blend optimization"
        title="Quantum Optimization Engine"
        description="Configure a QAOA blend-selection request. The interface models selection across whole candidate peptides, while sequence substitutions remain an upstream design step."
        action={<StatusPill tone="amber">Backend connection pending</StatusPill>}
      />

      <MockDataNotice detail="The candidate set, QAOA trajectory, coefficient values, and run metadata shown here are display fixtures. No Qiskit circuit has been executed and no blend has been optimized." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard detail="One binary variable per whole candidate" label="Problem size" value={`${demoBlendConfiguration.candidateCount} qubits`} />
        <MetricCard detail="Local UI selection target" label="Blend cardinality" value={`k = ${demoBlendConfiguration.selectedCount}`} />
        <MetricCard detail="For the 8-choose-3 reference configuration" label="Feasible subsets" value={`${demoBlendConfiguration.feasibleSubsets}`} />
        <MetricCard detail="Unconstrained binary encoding" label="Bitstrings" value={`${demoBlendConfiguration.bitstrings}`} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.93fr_1.07fr]">
        <Panel className="p-5">
          <div className="flex items-start gap-3">
            <span className="rounded-lg bg-[#EAF5F4] p-2 text-teal-700"><Cpu size={18} aria-hidden="true" /></span>
            <div>
              <p className="research-eyebrow">Algorithm settings</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]">QAOA run configuration</h2>
              <p className="mt-1 text-sm leading-6 text-[#657B85]">Fields are prepared for a future agreed API contract; changing them does not execute an experiment.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="research-label">Algorithm
              <select className="research-select mt-1.5" defaultValue="qaoa">
                <option value="qaoa">QAOA</option>
              </select>
            </label>
            <label className="research-label">QAOA layers (p)
              <input className="research-input mt-1.5" inputMode="numeric" min="1" onChange={(event) => setLayers(event.target.value)} value={layers} />
            </label>
            <label className="research-label">Execution target
              <select className="research-select mt-1.5" onChange={(event) => setExecutionTarget(event.target.value)} value={executionTarget}>
                <option value="simulator">Simulator (planned)</option>
                <option value="hardware">Hardware (unavailable)</option>
              </select>
            </label>
            <label className="research-label">Shot budget
              <input className="research-input mt-1.5" inputMode="numeric" min="1" onChange={(event) => setShots(event.target.value)} value={shots} />
            </label>
          </div>

          <label className="research-label mt-4">Objective documentation note
            <textarea className="research-textarea mt-1.5" defaultValue="Candidate scoring and pairwise terms are pending chemistry and quantum-team agreement." />
          </label>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button onClick={() => setReviewStatus(`Configuration reviewed locally: p=${layers}, ${shots} shots, ${executionTarget}. No backend request was made.`)}><ShieldCheck size={15} aria-hidden="true" /> Review configuration</Button>
            <Button disabled variant="secondary"><Play size={15} aria-hidden="true" /> Submit when API is connected</Button>
          </div>
          <p aria-live="polite" className="mt-3 text-xs leading-5 text-[#657B85]">{reviewStatus}</p>
        </Panel>

        <Panel className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Candidate selection context</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]">Whole-candidate blend preview</h2>
            </div>
            <StatusPill tone="demo">Display-only selection</StatusPill>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {selectedCandidates.map((candidate) => (
              <article key={candidate.id} className="rounded-lg border border-[#DCE7EC] bg-[#FBFDFD] p-3">
                <p className="font-mono text-[11px] text-teal-700">{candidate.id}</p>
                <p className="mt-1 text-sm font-semibold text-[#27424E]">{candidate.label}</p>
                <p className="mt-2 break-all font-mono text-xs tracking-[0.08em] text-[#647A84]">{candidate.sequence}</p>
              </article>
            ))}
          </div>
          <div className="mt-5 rounded-lg border border-[#DCE7EC] bg-[#F7FBFB] p-4 text-sm leading-6 text-[#516973]">
            <div className="flex items-start gap-2"><Database className="mt-0.5 shrink-0 text-teal-700" size={16} aria-hidden="true" /><p>Candidate IDs, descriptors, pairwise proxy terms, and the exact scoring contract must come from agreed backend responses before this preview can become an executable QUBO.</p></div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel className="p-5">
          <p className="research-eyebrow">Cost-function form</p>
          <h2 className="mt-1 text-lg font-semibold text-[#172B3A]">QUBO readiness</h2>
          <div className="mt-4 space-y-5">
            <label className="block">
              <span className="flex items-center justify-between text-sm font-medium text-[#36505C]"><span>γ — pairwise proxy weight</span><span className="font-mono text-xs text-teal-700">{gamma.toFixed(2)}</span></span>
              <input className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-[#D8E6E8] accent-[#087E78]" max="2" min="0" onChange={(event) => setGamma(Number(event.target.value))} step="0.05" type="range" value={gamma} />
            </label>
            <label className="block">
              <span className="flex items-center justify-between text-sm font-medium text-[#36505C]"><span>λ — cardinality penalty</span><span className="font-mono text-xs text-teal-700">{lambda.toFixed(2)}</span></span>
              <input className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-[#D8E6E8] accent-[#087E78]" max="5" min="0" onChange={(event) => setLambda(Number(event.target.value))} step="0.1" type="range" value={lambda} />
            </label>
          </div>
          <div className="mt-5"><QuboObjectivePanel blendSize={demoBlendConfiguration.selectedCount} gamma={gamma} lambda={lambda} /></div>
        </Panel>

        <Panel className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Optimization trace</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]">Illustrative convergence trajectory</h2>
              <p className="mt-1 text-sm leading-6 text-[#657B85]">Rendered from centralized demo data to validate the visualization only.</p>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-700"><Activity size={14} aria-hidden="true" /> DEMO only</span>
          </div>
          <div className="mt-3"><QaoaConvergenceChart /></div>
          <p className="border-t border-[#E5EEF0] pt-3 text-xs leading-5 text-[#6B818B]">Axes use arbitrary display units. This line is not a convergence record, a QAOA measurement, or a performance claim.</p>
        </Panel>
      </div>
    </div>
  )
}
