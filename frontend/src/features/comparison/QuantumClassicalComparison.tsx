import { CheckCircle2, Clock3, Equal, ShieldCheck } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { demoBenchmark, demoCandidates, demoProvenance } from '../../demo/researchDemo'
import { MetricCard, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { MockDataNotice } from '../shared/MockDataNotice'

const selectedCandidates = demoCandidates.filter((candidate) => candidate.selected)
const objectiveData = [
  { method: 'QAOA fixture', objective: demoBenchmark.qaoaObjective },
  { method: 'Exact fixture', objective: demoBenchmark.exactObjective },
]

const parityRows = [
  { metric: 'Candidate pool', quantum: '8 candidates', classical: '8 candidates', note: 'Same display fixture' },
  { metric: 'Selected blend size', quantum: 'k = 3', classical: 'k = 3', note: 'Same cardinality constraint' },
  { metric: 'Objective encoding', quantum: 'Pending contract', classical: 'Pending contract', note: 'Must match before benchmark' },
  { metric: 'Outcome provenance', quantum: 'Demo fixture', classical: 'Demo fixture', note: 'Not a measured run' },
]

export function QuantumClassicalComparison() {
  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Verification workspace"
        title="Quantum versus exact classical"
        description="A valid comparison uses the same candidate pool, objective, constraints, and declared execution context. The current values are display-only fixtures."
        action={<StatusPill tone="demo">No measured benchmark</StatusPill>}
      />

      <MockDataNotice detail={demoProvenance.detail} />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="Benchmark summary">
        <MetricCard label="QAOA objective" value={`${demoBenchmark.qaoaObjective.toFixed(2)} a.u.`} detail="Demo display only" />
        <MetricCard label="Exact objective" value={`${demoBenchmark.exactObjective.toFixed(2)} a.u.`} detail="Not an enumerated reference" />
        <MetricCard label="Optimality gap" value={`${demoBenchmark.optimalityGap.toFixed(2)} a.u.`} detail="Fixture arithmetic only" />
        <MetricCard label="Feasibility" value={`${Math.round(demoBenchmark.feasibilityRate * 100)}%`} detail="Not sampled bitstrings" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel className="p-5" aria-labelledby="objective-chart-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Objective comparison</p>
              <h2 id="objective-chart-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Display-only objective values</h2>
              <p className="mt-1 text-xs text-[#718791]">Arbitrary units. Not evidence of speedup, accuracy, or chemical validity.</p>
            </div>
            <StatusPill tone="demo">DEMO</StatusPill>
          </div>
          <div className="mt-5 h-64" role="img" aria-label="Demo QAOA and exact objective bar chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={objectiveData} margin={{ top: 10, right: 12, left: -8, bottom: 4 }}>
                <CartesianGrid stroke="#E5EEF0" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="method" tick={{ fill: '#5E747F', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#C9D9DE' }} />
                <YAxis domain={[0, 0.8]} tick={{ fill: '#5E747F', fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: 'Demo objective (a.u.)', angle: -90, position: 'insideLeft', fill: '#6B818B', fontSize: 11, dx: -2 }} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} a.u.`, 'Display value']} contentStyle={{ border: '1px solid #D9E0E7', borderRadius: 8, boxShadow: '0 4px 16px rgba(23,43,58,0.08)' }} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#5E747F' }} />
                <Bar dataKey="objective" name="Demo objective" fill="#087E78" radius={[4, 4, 0, 0]} maxBarSize={64} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="run-context-heading">
          <p className="research-eyebrow">Run context</p>
          <h2 id="run-context-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Required benchmark metadata</h2>
          <dl className="mt-5 grid gap-x-6 gap-y-4 sm:grid-cols-2">
            <div><dt className="text-xs font-medium text-[#6B818B]">Shot count</dt><dd className="mt-1 text-sm font-semibold text-[#28323C]">{demoBenchmark.shots.toLocaleString()} <span className="font-normal text-[#718791]">(demo)</span></dd></div>
            <div><dt className="text-xs font-medium text-[#6B818B]">Random seed</dt><dd className="mt-1 text-sm font-semibold text-[#28323C]">{demoBenchmark.seed} <span className="font-normal text-[#718791]">(demo)</span></dd></div>
            <div><dt className="text-xs font-medium text-[#6B818B]">QAOA runtime</dt><dd className="mt-1 text-sm font-semibold text-[#28323C]">{demoBenchmark.qaoaRuntimeMs} ms <span className="font-normal text-[#718791]">(demo)</span></dd></div>
            <div><dt className="text-xs font-medium text-[#6B818B]">Classical runtime</dt><dd className="mt-1 text-sm font-semibold text-[#28323C]">{demoBenchmark.classicalRuntimeMs} ms <span className="font-normal text-[#718791]">(demo)</span></dd></div>
          </dl>
          <div className="mt-5 rounded-lg border border-[#D9E0E7] bg-[#FAFCFC] p-4">
            <p className="text-sm font-semibold text-[#394957]">Selected display blend</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedCandidates.map((candidate) => <span key={candidate.id} className="rounded-md border border-[#D6E3E6] bg-white px-2 py-1 font-mono text-xs text-[#36505C]">{candidate.id}</span>)}
            </div>
            <p className="mt-3 text-xs leading-5 text-[#718791]">A future response must supply the actual selected IDs, bitstring interpretation, constraint result, and source-specific provenance.</p>
          </div>
        </Panel>
      </section>

      <Panel className="p-5" aria-labelledby="parity-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="research-eyebrow">Comparison controls</p>
            <h2 id="parity-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Parity checklist</h2>
          </div>
          <StatusPill tone="amber">Contract pending</StatusPill>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="research-table min-w-[42rem]">
            <thead><tr><th>Metric</th><th>QAOA / quantum</th><th>Exact classical</th><th>Interpretation</th></tr></thead>
            <tbody>
              {parityRows.map((row) => <tr key={row.metric}><td className="font-semibold text-[#394957]">{row.metric}</td><td>{row.quantum}</td><td>{row.classical}</td><td className="text-[#718791]">{row.note}</td></tr>)}
            </tbody>
          </table>
        </div>
      </Panel>

      <section className="grid gap-4 md:grid-cols-3" aria-label="Benchmarking guardrails">
        <Panel className="p-4"><Equal className="text-blue-700" size={18} /><h3 className="mt-3 text-sm font-semibold text-[#394957]">Same objective</h3><p className="mt-1 text-xs leading-5 text-[#718791]">The direct scoring function and QUBO must agree before comparison.</p></Panel>
        <Panel className="p-4"><CheckCircle2 className="text-blue-700" size={18} /><h3 className="mt-3 text-sm font-semibold text-[#394957]">Feasibility first</h3><p className="mt-1 text-xs leading-5 text-[#718791]">Report constraint satisfaction alongside objective values and selected candidates.</p></Panel>
        <Panel className="p-4"><ShieldCheck className="text-blue-700" size={18} /><h3 className="mt-3 text-sm font-semibold text-[#394957]">No advantage claim</h3><p className="mt-1 text-xs leading-5 text-[#718791]">Runtime and sampling context inform a study; they do not alone establish quantum advantage.</p></Panel>
      </section>

      <div className="flex items-center gap-2 text-xs text-[#718791]"><Clock3 size={14} /> Backend benchmark data will replace this fixture once an agreed response contract exists.</div>
    </div>
  )
}
