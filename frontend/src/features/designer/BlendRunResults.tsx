import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Button, MetricCard, Panel, StatusPill } from '../../components/ui'
import type { BlendResult } from '../../services/blendResearch'

export function BlendRunResults({ result }: { result: BlendResult }) {
  function downloadCircuit() {
    const url = URL.createObjectURL(new Blob([result.circuit_qasm], { type: 'text/plain' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'peptide_blend_qaoa.qasm'
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const percent = (value: number) => `${(100 * value).toFixed(1)}%`
  return (
    <Panel className="min-w-0 space-y-5 p-5" aria-label="Calculated blend research results">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="research-eyebrow">Latest calculated research run</p><h2 className="mt-1 text-lg font-semibold">QAOA-selected peptide candidates</h2></div>
        <StatusPill tone="blue">Qiskit simulator result</StatusPill>
      </div>
      <p className="text-sm leading-6 text-[#526A75]">
        {result.candidates.length} whole-peptide variables, select {result.goals.blend_size}. pH {result.goals.ph};
        target charge {result.goals.target_charge} e; target hydropathy {result.goals.target_hydropathy}.
        This is a sequence-property research selection, not a tested physical blend.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Feasible sampled outcomes" value={percent(result.benchmark.observed_feasibility_rate)} detail={`Uniform baseline: ${percent(result.benchmark.uniform_feasible_probability)}`} />
        <MetricCard label="Probability of an optimum" value={percent(result.benchmark.optimum_probability)} detail={`Uniform baseline: ${percent(result.benchmark.uniform_optimum_probability)}`} />
        <MetricCard label="Sampled objective gap" value={result.benchmark.sampled_objective_gap === null ? 'No feasible sample' : result.benchmark.sampled_objective_gap.toFixed(5)} detail="Lower is better; 0 matches the pool's exact optimum" />
        <MetricCard label="Exact feasible search" value={`${result.benchmark.feasible_subset_count} subsets`} detail={`${result.benchmark.bitstring_count} total bitstrings; ${result.shots} simulated shots`} />
      </div>
      {result.selected_blend ? (
        <div className="grid gap-3 md:grid-cols-3">
          {result.selected_blend.candidates.map((candidate) => (
            <article className="rounded-lg border border-teal-200 bg-teal-50/40 p-4" key={candidate.id}>
              <h3 className="font-semibold text-[#214652]">{candidate.name}</h3>
              <p className="mt-2 break-all font-mono text-xs text-[#526A75]">{candidate.sequence}</p>
              <dl className="mt-3 space-y-1 text-xs text-[#526A75]">
                <div>Score: {candidate.score?.toFixed(4)}</div><div>Estimated charge: {candidate.charge?.toFixed(3)} e</div>
                <div>Hydropathy: {candidate.hydropathy?.toFixed(3)}</div><div>Mass: {candidate.mass_da?.toFixed(1)} Da</div>
              </dl>
              <a className="mt-3 inline-block text-xs font-semibold text-teal-800 underline" href={candidate.source_url} rel="noreferrer" target="_blank">Source: {candidate.source} / {candidate.accession}</a>
            </article>
          ))}
        </div>
      ) : <p role="status" className="rounded-lg bg-amber-50 p-4 text-sm text-amber-900">No feasible blend was observed. The classical reference below is separate and has not been substituted as a QAOA result.</p>}
      <div className="rounded-lg bg-[#F4F8F9] p-4 text-sm leading-6 text-[#526A75]">
        {result.selected_blend && <p>Selected bitstring: <code>{result.selected_blend.bitstring}</code> (rightmost bit selects candidate 0). Objective = -{result.selected_blend.individual_score_sum.toFixed(5)} individual score + {result.selected_blend.weighted_redundancy_penalty.toFixed(5)} weighted sequence redundancy. Exactly {result.goals.blend_size} candidates required.</p>}
        <p><strong>Exact classical reference:</strong> {result.classical_reference.candidates.map((candidate) => candidate.name).join(', ')}.</p>
        <p>Exact objective: {result.classical_reference.objective.toFixed(5)}. QAOA sampled objective: {result.selected_blend?.objective.toFixed(5) ?? 'unavailable'}. Lower is better.</p>
        <p>Convergence: {result.converged ? 'criterion reached' : 'not reached within the evaluation budget'}. {result.optimizer_message}</p>
      </div>
      <div>
        <h3 className="mb-3 text-sm font-semibold">Actual QAOA evaluation history</h3>
        <div className="h-56 min-w-0" aria-label="Expected penalized objective during QAOA fitting">
          <ResponsiveContainer width="100%" height="100%"><LineChart data={result.history} margin={{ left: 15, right: 15 }}>
            <XAxis dataKey="evaluation" /><YAxis width={55} /><Tooltip />
            <Line type="linear" dataKey="expected_penalized_objective" name="Expected penalized objective" stroke="#0f766e" dot={false} isAnimationActive={false} />
          </LineChart></ResponsiveContainer>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs text-[#607883]">
        <Button onClick={downloadCircuit} variant="secondary">Download blend circuit for IBM Composer</Button>
        <span>{result.evaluations} evaluations · {result.elapsed_seconds.toFixed(2)} s · seed {result.goals.seed} · depth {result.circuit_depth}</span>
      </div>
      <details className="text-xs leading-6 text-[#607883]"><summary className="cursor-pointer font-semibold">Scoring methods and limitations</summary>
        <dl className="mt-3 space-y-2">{Object.entries(result.scoring_method).map(([key, value]) => <div key={key}><dt className="font-semibold">{key.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}</dl>
        <ul className="mt-4 list-disc space-y-1 pl-5">{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      </details>
    </Panel>
  )
}
