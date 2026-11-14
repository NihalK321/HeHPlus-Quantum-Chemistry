import { Activity, ArrowRight, Atom, Beaker, ListChecks, Play, SlidersHorizontal } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { demoBlendConfiguration, demoCandidates, demoConvergence, demoProvenance } from '../../demo/researchDemo'
import { Button, MetricCard, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { MockDataNotice } from '../shared/MockDataNotice'
import { LatestBlendRun } from './LatestBlendRun'

const readiness = [
  { label: 'Candidate pool', detail: '8 display-only candidates staged', tone: 'blue' as const, icon: ListChecks },
  { label: 'Chemistry descriptors', detail: 'Awaiting documented calculation method', tone: 'amber' as const, icon: Beaker },
  { label: 'Exact baseline', detail: 'Awaiting backend enumeration', tone: 'amber' as const, icon: Activity },
]

const selectedCandidates = demoCandidates.filter((candidate) => candidate.selected)

export function ResearchDashboard() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Research workspace"
        title="Blend optimization overview"
        description="Configure a peptide candidate pool, document chemistry assumptions, and compare an eventual QAOA result with the exact classical reference."
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" className="hidden sm:inline-flex" onClick={() => undefined}>
              <SlidersHorizontal size={15} />
              Review settings
            </Button>
            <Button onClick={() => navigate('/designer')}>
              <Play size={15} />
              Configure experiment
            </Button>
          </div>
        }
      />

      <LatestBlendRun />

      <MockDataNotice detail={`The legacy dashboard panels below are demo data. ${demoProvenance.detail}`} />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="Experiment summary">
        <MetricCard label="Candidate pool" value={`${demoBlendConfiguration.candidateCount}`} detail="Display-only candidate records" />
        <MetricCard label="Target blend" value={`${demoBlendConfiguration.selectedCount} peptides`} detail="Selection count k" />
        <MetricCard label="Feasible subsets" value={`${demoBlendConfiguration.feasibleSubsets}`} detail="8 choose 3 reference configuration" />
        <MetricCard label="Optimization state" value="Draft" detail="No QAOA job submitted" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel className="p-5" aria-labelledby="configuration-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Current configuration</p>
              <h2 id="configuration-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Research inputs</h2>
            </div>
            <StatusPill tone="demo">Demo fixture</StatusPill>
          </div>
          <dl className="mt-5 grid gap-x-6 gap-y-5 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-[#6B818B]">Target pH</dt>
              <dd className="mt-1 text-sm font-semibold text-[#28323C]">{demoBlendConfiguration.targetPh}</dd>
              <p className="mt-1 text-xs text-[#718791]">UI setting; no calculation performed</p>
            </div>
            <div>
              <dt className="text-xs font-medium text-[#6B818B]">Temperature context</dt>
              <dd className="mt-1 text-sm font-semibold text-[#28323C]">{demoBlendConfiguration.temperature}</dd>
              <p className="mt-1 text-xs text-[#718791]">UI setting; no experimental record</p>
            </div>
            {demoBlendConfiguration.propertyWeights.map((weight) => (
              <div key={weight.label}>
                <dt className="text-xs font-medium text-[#6B818B]">{weight.label}</dt>
                <dd className="mt-1 flex items-center gap-3">
                  <span className="text-sm font-semibold text-[#28323C]">{Math.round(weight.value * 100)}%</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EAF0F2]" aria-hidden="true">
                    <span className="block h-full rounded-full bg-blue-700" style={{ width: `${weight.value * 100}%` }} />
                  </span>
                </dd>
              </div>
            ))}
          </dl>
          <div className="mt-6 flex justify-end border-t border-[#E5EEF0] pt-4">
            <Link className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-700 hover:text-blue-800" to="/designer">
              Edit research inputs <ArrowRight size={15} />
            </Link>
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="blend-heading">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Selected blend</p>
              <h2 id="blend-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Draft candidate subset</h2>
            </div>
            <StatusPill tone="amber">Not optimized</StatusPill>
          </div>
          <ul className="mt-4 divide-y divide-[#E8EFF1]">
            {selectedCandidates.map((candidate) => (
              <li key={candidate.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[#394957]">{candidate.id} · {candidate.label}</p>
                  <p className="mt-0.5 truncate font-mono text-xs tracking-[0.08em] text-[#5E747F]">{candidate.sequence}</p>
                </div>
                <StatusPill tone="slate">Candidate</StatusPill>
              </li>
            ))}
          </ul>
          <p className="mt-4 rounded-md bg-[#F4F8F8] p-3 text-xs leading-5 text-[#58707A]">
            This subset is a display-only interface selection. QAOA will select complete candidates, not amino acids at individual positions.
          </p>
        </Panel>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel className="p-5" aria-labelledby="convergence-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Optimization trace</p>
              <h2 id="convergence-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Demo objective trace</h2>
              <p className="mt-1 text-xs text-[#718791]">Illustrative values in arbitrary units; not a QAOA execution.</p>
            </div>
            <StatusPill tone="demo">DEMO</StatusPill>
          </div>
          <div className="mt-5 h-60" role="img" aria-label="Demo objective trace chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={demoConvergence} margin={{ top: 8, right: 16, left: -10, bottom: 4 }}>
                <CartesianGrid stroke="#E5EEF0" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="iteration" tick={{ fill: '#6B818B', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#C9D9DE' }} label={{ value: 'Iteration', position: 'insideBottom', offset: -2, fill: '#6B818B', fontSize: 11 }} />
                <YAxis tick={{ fill: '#6B818B', fontSize: 11 }} tickLine={false} axisLine={false} domain={[0.5, 1.05]} label={{ value: 'Demo objective (a.u.)', angle: -90, position: 'insideLeft', fill: '#6B818B', fontSize: 11, dx: -3 }} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} a.u.`, 'Demo objective']} contentStyle={{ border: '1px solid #D9E0E7', borderRadius: 8, boxShadow: '0 4px 16px rgba(23,43,58,0.08)' }} />
                <Line type="monotone" dataKey="objective" stroke="#087E78" strokeWidth={2.25} dot={{ r: 3, fill: '#087E78' }} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="readiness-heading">
          <p className="research-eyebrow">Workflow readiness</p>
          <h2 id="readiness-heading" className="mt-1 text-lg font-semibold text-[#28323C]">What is connected?</h2>
          <div className="mt-5 space-y-4">
            {readiness.map((item) => {
              const Icon = item.icon
              return (
                <div key={item.label} className="flex items-start gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-[#EFF6F5] text-blue-700"><Icon size={16} /></span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-[#394957]">{item.label}</p>
                      <StatusPill tone={item.tone}>{item.tone === 'blue' ? 'Ready for UI' : 'Pending'}</StatusPill>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-[#718791]">{item.detail}</p>
                  </div>
                </div>
              )
            })}
          </div>
          <Link className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-blue-700 hover:text-blue-800" to="/optimization">
            Open optimization workspace <ArrowRight size={15} />
          </Link>
        </Panel>
      </section>

      <Panel className="p-5" aria-labelledby="guardrails-heading">
        <div className="flex gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[#F2F6F7] text-[#52707B]"><Atom size={18} /></span>
          <div>
            <p className="research-eyebrow">Research guardrail</p>
            <h2 id="guardrails-heading" className="mt-1 text-base font-semibold text-[#28323C]">Keep evidence types separate</h2>
            <p className="mt-1.5 max-w-4xl text-sm leading-6 text-[#5E747F]">The interface distinguishes UI fixtures, calculated descriptors, simulated QAOA output, and hardware measurements. A chemistry proxy or structural hypothesis is never presented as clinical safety, synergy, or laboratory-confirmed compatibility.</p>
          </div>
        </div>
      </Panel>
    </div>
  )
}
