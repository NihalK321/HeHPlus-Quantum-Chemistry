import { useMemo, useState } from 'react'
import { RotateCcw, SlidersHorizontal } from 'lucide-react'
import { demoProvenance, demoTradeoffPoints } from '../../demo/researchDemo'
import { Button, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { MockDataNotice } from '../shared/MockDataNotice'
import { TradeoffVisualizations } from './TradeoffVisualizations'

export function OptimizationTradeoffExplorer() {
  const [chargeWeight, setChargeWeight] = useState(0.5)
  const hydropathyWeight = 1 - chargeWeight

  const rankedBlends = useMemo(() => demoTradeoffPoints
    .map((point) => ({ ...point, score: point.charge * chargeWeight + point.hydropathy * hydropathyWeight }))
    .sort((first, second) => second.score - first.score), [chargeWeight, hydropathyWeight])

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Sensitivity workspace"
        title="Optimization trade-off explorer"
        description="Inspect how declared objective emphasis changes a display-only blend ranking. This interface does not calculate chemistry or re-run an optimizer."
        action={<StatusPill tone="demo">Demo sensitivity view</StatusPill>}
      />

      <MockDataNotice detail={demoProvenance.detail} />

      <section className="grid gap-5 xl:grid-cols-[0.78fr_1.22fr]">
        <Panel className="p-5" aria-labelledby="weights-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[#EFF6F5] text-blue-700"><SlidersHorizontal size={18} /></span>
            <div>
              <p className="research-eyebrow">Objective weights</p>
              <h2 id="weights-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Display-only weighting controls</h2>
            </div>
          </div>

          <div className="mt-6 space-y-6">
            <label className="block">
              <span className="flex items-center justify-between gap-3 text-sm font-semibold text-[#36505C]"><span>Charge target</span><span className="font-mono text-xs text-blue-700">{Math.round(chargeWeight * 100)}%</span></span>
              <input className="mt-3 w-full accent-blue-700" type="range" min="0" max="100" value={Math.round(chargeWeight * 100)} onChange={(event) => setChargeWeight(Number(event.target.value) / 100)} aria-label="Charge target weight" />
              <p className="mt-2 text-xs leading-5 text-[#718791]">Changes only the central demo score formula, not a chemistry model.</p>
            </label>
            <label className="block">
              <span className="flex items-center justify-between gap-3 text-sm font-semibold text-[#36505C]"><span>Hydropathy target</span><span className="font-mono text-xs text-blue-700">{Math.round(hydropathyWeight * 100)}%</span></span>
              <input className="mt-3 w-full accent-blue-700" type="range" min="0" max="100" value={Math.round(hydropathyWeight * 100)} onChange={(event) => setChargeWeight(1 - Number(event.target.value) / 100)} aria-label="Hydropathy target weight" />
              <p className="mt-2 text-xs leading-5 text-[#718791]">The two UI weights are constrained to sum to 100% for this illustration.</p>
            </label>
          </div>

          <div className="mt-6 rounded-lg border border-[#D9E0E7] bg-[#F8FAFC] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6B818B]">Defined display formula</p>
            <p className="mt-2 font-mono text-xs leading-6 text-[#36505C]">score = charge fixture × charge weight + hydropathy fixture × hydropathy weight</p>
            <p className="mt-2 text-xs leading-5 text-[#718791]">This is intentionally not the chemistry scoring contract or a QUBO objective.</p>
          </div>

          <Button variant="secondary" className="mt-5 w-full" onClick={() => setChargeWeight(0.5)}><RotateCcw size={15} /> Reset display weights</Button>
        </Panel>

        <Panel className="p-5" aria-labelledby="ranked-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Responsive display ranking</p>
              <h2 id="ranked-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Fixture ranking after UI weighting</h2>
              <p className="mt-1 text-xs text-[#718791]">The order updates locally when the sliders move; it does not represent a selected scientific blend.</p>
            </div>
            <StatusPill tone="demo">DEMO</StatusPill>
          </div>
          <ol className="mt-5 space-y-3">
            {rankedBlends.map((blend, index) => (
              <li key={blend.id} className="flex items-center gap-3 rounded-lg border border-[#E3ECEE] bg-[#FCFEFE] p-3">
                <span className="grid h-7 w-7 place-items-center rounded-md bg-[#EAF4F3] text-xs font-bold text-blue-800">{index + 1}</span>
                <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-[#394957]">{blend.id}</p><p className="mt-0.5 text-xs text-[#718791]">Charge fixture {blend.charge.toFixed(2)} a.u. · Hydropathy fixture {blend.hydropathy.toFixed(2)} a.u.</p></div>
                <div className="text-right"><p className="font-mono text-sm font-semibold text-[#394957]">{blend.score.toFixed(3)}</p><p className="text-[11px] text-[#718791]">display score</p></div>
              </li>
            ))}
          </ol>
        </Panel>
      </section>

      <TradeoffVisualizations chargeWeight={chargeWeight} hydropathyWeight={hydropathyWeight} />

      <Panel className="p-5" aria-labelledby="interpretation-heading">
        <p className="research-eyebrow">Interpretation note</p>
        <h2 id="interpretation-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Sensitivity is not compatibility evidence</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-[#5E747F]">When a backend scoring contract is available, this page can request a defined sensitivity study and show the selected candidate blends, constraints, proxy terms, and provenance for each scenario. Until then, the interactive controls operate only on labeled interface fixtures.</p>
      </Panel>
    </div>
  )
}
