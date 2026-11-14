import { useMemo, useState } from 'react'
import { Braces, CircuitBoard, FlaskConical, Info, Orbit, Workflow } from 'lucide-react'
import { Button, EmptyState, MetricCard, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { createUnavailableHehExperiment } from '../../types/quantumChemistry'
import type { HeHExperiment, HeHEnergyPoint } from '../../types/quantumChemistry'
import { HeHStructureDiagram } from './HeHStructureDiagram'
import { ChartContextNote, EnergyErrorChart, PotentialEnergySurfaceChart, VqeConvergenceChart } from './HeHEnergyVisualizations'

const bondDistanceOptions = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3]

function statusTone(status: HeHExperiment['calculationStatus']): 'teal' | 'amber' | 'slate' | 'red' {
  if (status === 'completed') return 'teal'
  if (status === 'failed') return 'red'
  if (status === 'queued' || status === 'running') return 'amber'
  return 'slate'
}

function statusLabel(status: HeHExperiment['calculationStatus']): string {
  return status.replace('_', ' ')
}

function displaySpecified(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '' || value === 'not_specified') return 'Not yet specified'
  return typeof value === 'string' ? value.replaceAll('_', ' ') : String(value)
}

function formatEnergy(value: number | null): string {
  return value === null ? 'Unavailable' : `${value.toFixed(8)} Ha`
}

/**
 * Quantum chemistry is intentionally separate from the peptide QAOA workflow.
 * The page renders an unavailable experiment until verified VQE backend data is
 * supplied through the frontend service contract.
 */
export function HeHQuantumChemistry({ experiment = createUnavailableHehExperiment() }: { experiment?: HeHExperiment }) {
  const [bondDistance, setBondDistance] = useState(1.0)
  const selectedConvergence = useMemo(
    () => experiment.convergenceHistory.find((entry) => Math.abs(entry.bondDistanceAngstrom - bondDistance) < 0.0001)?.points ?? [],
    [bondDistance, experiment.convergenceHistory],
  )
  const availableEnergyPoints = experiment.energyPoints.filter((point) => point.vqeEnergyHartree !== null || point.referenceEnergyHartree !== null)
  const minimumPoint = availableEnergyPoints.reduce<HeHEnergyPoint | undefined>((minimum, point) => {
    const energy = point.referenceEnergyHartree ?? point.vqeEnergyHartree
    const minimumEnergy = minimum ? minimum.referenceEnergyHartree ?? minimum.vqeEnergyHartree : undefined
    if (energy === null) return minimum
    if (minimumEnergy === undefined || minimumEnergy === null || energy < minimumEnergy) return point
    return minimum
  }, undefined)

  const methodology = [
    { label: 'Ansatz', value: displaySpecified(experiment.method.ansatz), rationale: experiment.method.ansatz ? 'Configuration received; include the backend’s scientific justification with the experiment record.' : 'Not yet specified by a calculation record.' },
    { label: 'Fermion-to-qubit mapping', value: displaySpecified(experiment.method.fermionToQubitMapping), rationale: experiment.method.fermionToQubitMapping ? 'Configuration received; mapping rationale must be documented by the quantum workflow.' : 'Not yet specified by a calculation record.' },
    { label: 'Classical optimizer', value: displaySpecified(experiment.method.classicalOptimizer), rationale: experiment.method.classicalOptimizer ? 'Configuration received; convergence behavior must be assessed from the completed run.' : 'Not yet specified by a calculation record.' },
    { label: 'Classical reference method', value: displaySpecified(experiment.method.classicalReferenceMethod), rationale: experiment.method.classicalReferenceMethod ? 'The reference must retain the same molecular model, basis, and energy convention as the VQE comparison.' : 'Not yet specified by a calculation record.' },
    { label: 'Basis set', value: displaySpecified(experiment.method.basisSet), rationale: experiment.method.basisSet ? 'Configuration received; the classical reference must use the same molecular model and basis.' : 'Not yet specified by a calculation record.' },
  ]

  const calculationBoundary = experiment.calculationStatus === 'unavailable' || experiment.calculationStatus === 'not_started'
    ? 'No verified HeH+ VQE experiment is connected. The current page is a backend-ready empty state: it shows molecular facts and a geometry diagram, but no molecular energy or algorithm metadata is invented.'
    : `This experiment is marked ${statusLabel(experiment.calculationStatus)}. Only metadata and result fields supplied by its backend record are shown; omitted values remain “Not yet specified” or unavailable.`

  return (
    <div className="space-y-6">
      <SectionHeading
        action={<StatusPill tone={statusTone(experiment.calculationStatus)}>{statusLabel(experiment.calculationStatus)}</StatusPill>}
        description="A separate VQE electronic-structure study of the helium hydride ion. It does not share a Hamiltonian, objective, or interpretation with peptide-blend QAOA optimization."
        eyebrow="Quantum chemistry workspace"
        title="Quantum Chemistry — HeH+"
      />

      <Panel className="border-[#D7E7E9] bg-[#FBFDFD] p-4" role="note">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-teal-700" aria-hidden="true" />
          <div className="text-sm leading-6 text-[#49636D]">
            <p className="font-semibold text-[#27424E]">Calculation boundary</p>
            <p className="mt-1">{calculationBoundary}</p>
          </div>
        </div>
      </Panel>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Molecular overview">
        <MetricCard detail="Helium hydride ion" label="Molecule" value="HeH+" />
        <MetricCard detail="Molecular charge" label="Charge" value="+1" />
        <MetricCard detail="For the stated molecular charge" label="Electron count" value="2" />
        <MetricCard detail="Geometry selector only; no energy calculated" label="Selected He–H separation" value={`${bondDistance.toFixed(2)} Å`} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel className="p-5" aria-labelledby="geometry-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-teal-50 text-teal-700"><Orbit className="h-[18px] w-[18px]" aria-hidden="true" /></span>
            <div>
              <p className="research-eyebrow">Molecular overview</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="geometry-heading">Explore nuclear separation</h2>
              <p className="mt-1 text-sm leading-6 text-[#657B85]">Move the selected He–H distance to inspect the geometry sent to a future experiment. This diagram is not an electronic-structure calculation.</p>
            </div>
          </div>

          <div className="mt-6">
            <label className="research-label" htmlFor="heh-bond-distance">He–H bond distance</label>
            <div className="mt-2 flex items-center gap-3">
              <input
                className="h-1.5 min-w-0 flex-1 cursor-pointer appearance-none rounded-full bg-[#D8E6E8] accent-[#087E78]"
                id="heh-bond-distance"
                max="3"
                min="0.5"
                onChange={(event) => setBondDistance(Number(event.target.value))}
                step="0.05"
                type="range"
                value={bondDistance}
              />
              <output className="w-20 rounded-md border border-[#DCE7EC] bg-white px-2 py-1.5 text-right font-mono text-sm text-[#27424E]}" htmlFor="heh-bond-distance">
                {bondDistance.toFixed(2)} Å
              </output>
            </div>
            <div className="mt-3 flex flex-wrap gap-2" aria-label="Common bond distances">
              {bondDistanceOptions.map((distance) => (
                <button
                  className={`rounded-md border px-2 py-1 text-xs font-semibold transition-colors ${Math.abs(distance - bondDistance) < 0.001 ? 'border-teal-700 bg-teal-700 text-white' : 'border-[#DCE7EC] bg-white text-[#526A75] hover:border-teal-600 hover:bg-teal-50'}`}
                  key={distance}
                  onClick={() => setBondDistance(distance)}
                  type="button"
                >
                  {distance.toFixed(2)} Å
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-[#DCE7EC] bg-white p-4">
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div><dt className="text-xs font-medium text-[#6B818B]">Energy convention</dt><dd className="mt-1 font-semibold text-[#27424E]">{displaySpecified(experiment.energyConvention)}</dd></div>
              <div><dt className="text-xs font-medium text-[#6B818B]">Nuclear-repulsion treatment</dt><dd className="mt-1 font-semibold text-[#27424E]">{displaySpecified(experiment.nuclearRepulsionTreatment)}</dd></div>
              <div><dt className="text-xs font-medium text-[#6B818B]">Calculation provenance</dt><dd className="mt-1 font-semibold text-[#27424E]">{experiment.provenance.label}</dd></div>
            </dl>
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="diagram-heading">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">Bond-distance diagram</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="diagram-heading">HeH+ nuclear geometry</h2>
            </div>
            <StatusPill tone="slate">Geometry only</StatusPill>
          </div>
          <div className="mt-4"><HeHStructureDiagram bondDistanceAngstrom={bondDistance} /></div>
          <p className="mt-4 text-xs leading-5 text-[#6B818B]">Helium is placed at the origin and hydrogen along the internuclear axis for visualization. The displayed separation is a coordinate choice, not a predicted equilibrium geometry.</p>
        </Panel>
      </section>

      <Panel className="p-5" aria-labelledby="pes-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="research-eyebrow">Potential energy surface</p>
            <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="pes-heading">VQE and classical-reference energy curve</h2>
            <p className="mt-1 text-sm leading-6 text-[#657B85]">Both series must use a consistent molecular model, charge, electron count, basis, and explicit energy convention.</p>
          </div>
          {minimumPoint ? <StatusPill tone="teal">Minimum at {minimumPoint.bondDistanceAngstrom.toFixed(3)} Å</StatusPill> : <StatusPill tone="slate">No curve data</StatusPill>}
        </div>
        <div className="mt-5"><PotentialEnergySurfaceChart energyConvention={experiment.energyConvention} points={experiment.energyPoints} /></div>
        <ChartContextNote>The x-axis uses Angstroms; the y-axis label follows the energy convention supplied by the backend. A minimum is identified only when calculated or reference energy points are supplied.</ChartContextNote>
      </Panel>

      <Panel className="p-5" aria-labelledby="error-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="research-eyebrow">Comparison diagnostic</p>
            <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="error-heading">VQE energy error by geometry</h2>
            <p className="mt-1 text-sm leading-6 text-[#657B85]">Error is shown only when the record includes both a VQE value and a scientifically comparable classical reference.</p>
          </div>
          <StatusPill tone={experiment.energyPoints.some((point) => point.absoluteErrorHartree !== null) ? 'teal' : 'slate'}>
            {experiment.energyPoints.some((point) => point.absoluteErrorHartree !== null) ? 'Error data available' : 'No error data'}
          </StatusPill>
        </div>
        <div className="mt-5"><EnergyErrorChart points={experiment.energyPoints} /></div>
        <ChartContextNote>Absolute error and any VQE uncertainty are reported in Hartrees. They do not establish accuracy without the shared method, basis, and energy-convention metadata.</ChartContextNote>
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel className="p-5" aria-labelledby="algorithm-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[#EEF6F5] text-teal-700"><CircuitBoard className="h-[18px] w-[18px]" aria-hidden="true" /></span>
            <div>
              <p className="research-eyebrow">Quantum algorithm explorer</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="algorithm-heading">Method configuration</h2>
              <p className="mt-1 text-sm leading-6 text-[#657B85]">Values remain intentionally unspecified until the quantum backend returns verified experiment metadata.</p>
            </div>
          </div>
          <dl className="mt-5 divide-y divide-[#E6EFF1] text-sm">
            <MethodRow label="Ansatz" value={displaySpecified(experiment.method.ansatz)} />
            <MethodRow label="Fermion-to-qubit mapping" value={displaySpecified(experiment.method.fermionToQubitMapping)} />
            <MethodRow label="Classical optimizer" value={displaySpecified(experiment.method.classicalOptimizer)} />
            <MethodRow label="Classical reference method" value={displaySpecified(experiment.method.classicalReferenceMethod)} />
            <MethodRow label="Basis set" value={displaySpecified(experiment.method.basisSet)} />
            <MethodRow label="Qubits" value={displaySpecified(experiment.method.qubitCount)} />
            <MethodRow label="Variational parameters" value={displaySpecified(experiment.method.variationalParameterCount)} />
            <MethodRow label="Circuit depth" value={displaySpecified(experiment.method.circuitDepth)} />
            <MethodRow label="Optimization iterations" value={displaySpecified(experiment.method.optimizerIterations)} />
          </dl>
          <div className="mt-5 rounded-md border border-[#DCE7EC] bg-[#FBFDFD] p-3 text-xs leading-5 text-[#657B85]">
            Circuit visualization is withheld until the backend provides approved circuit data and its experiment-level provenance.
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="convergence-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="research-eyebrow">VQE convergence</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="convergence-heading">Selected geometry: {bondDistance.toFixed(2)} Å</h2>
              <p className="mt-1 text-sm leading-6 text-[#657B85]">A completed run can attach a convergence history to this bond distance.</p>
            </div>
            <StatusPill tone={selectedConvergence.length > 0 ? 'teal' : 'slate'}>{selectedConvergence.length > 0 ? 'History available' : 'No history'}</StatusPill>
          </div>
          <div className="mt-5"><VqeConvergenceChart points={selectedConvergence} /></div>
          <ChartContextNote>Convergence plots must distinguish VQE estimates from a classical reference and identify the selected geometry and calculation provenance.</ChartContextNote>
        </Panel>
      </section>

      <Panel className="p-5" aria-labelledby="energy-table-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="research-eyebrow">Molecular energy comparison</p>
            <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="energy-table-heading">Calculation records</h2>
            <p className="mt-1 text-sm leading-6 text-[#657B85]">The table exposes VQE, reference, and error fields only when an experiment supplies them.</p>
          </div>
          <Button disabled variant="secondary"><Workflow className="h-4 w-4" aria-hidden="true" /> Await backend experiment</Button>
        </div>
        {experiment.energyPoints.length === 0 ? (
          <div className="mt-5"><EmptyState detail="No completed HeH+ calculation has supplied energy points. The table will retain units and provenance once results are available." title="No energy-comparison records" /></div>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="research-table min-w-[76rem]">
              <thead><tr><th>Bond distance (Å)</th><th>VQE energy (Ha)</th><th>VQE uncertainty (Ha)</th><th>Reference energy (Ha)</th><th>Absolute error (Ha)</th><th>Relative error</th><th>Notes</th><th>Provenance</th></tr></thead>
              <tbody>
                {experiment.energyPoints.map((point) => (
                  <tr key={point.bondDistanceAngstrom}>
                    <td className="font-mono text-[#27424E]">{point.bondDistanceAngstrom.toFixed(3)}</td>
                    <td>{formatEnergy(point.vqeEnergyHartree)}</td>
                    <td>{formatEnergy(point.vqeEnergyUncertaintyHartree)}</td>
                    <td>{formatEnergy(point.referenceEnergyHartree)}</td>
                    <td>{formatEnergy(point.absoluteErrorHartree)}</td>
                    <td>{point.relativeError === null ? 'Unavailable' : point.relativeError.toExponential(3)}</td>
                    <td className="max-w-56 whitespace-normal text-xs text-[#657B85]">{point.notes ?? '—'}</td>
                    <td><span className="text-xs text-[#657B85]">{point.provenance.label}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel className="p-5" aria-labelledby="methodology-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[#F1F6F7] text-[#45636E]"><Braces className="h-[18px] w-[18px]" aria-hidden="true" /></span>
            <div>
              <p className="research-eyebrow">Methodology and justification</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="methodology-heading">Choices require a documented calculation record</h2>
            </div>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {methodology.map((item) => (
              <article className="rounded-lg border border-[#E1EBEE] bg-[#FCFEFE] p-4" key={item.label}>
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6B818B]">{item.label}</p>
                <p className="mt-2 text-sm font-semibold text-[#27424E]">{item.value}</p>
                <p className="mt-2 text-xs leading-5 text-[#718791]">{item.rationale}</p>
              </article>
            ))}
          </div>
          <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
            A classical reference is scientifically comparable only within the same molecular model and basis. The energy convention must explicitly state whether nuclear repulsion is included.
          </div>
        </Panel>

        <Panel className="p-5" aria-labelledby="limits-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[#F5F8F9] text-[#52717B]"><FlaskConical className="h-[18px] w-[18px]" aria-hidden="true" /></span>
            <div>
              <p className="research-eyebrow">Scientific boundaries</p>
              <h2 className="mt-1 text-lg font-semibold text-[#172B3A]" id="limits-heading">Interpret with calculation context</h2>
            </div>
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-6 text-[#5E747F]">
            <li>VQE is an electronic-structure workflow; it is not the QAOA peptide-selection model.</li>
            <li>The diagram encodes only an internuclear separation and cannot establish a potential-energy minimum.</li>
            <li>Method, convergence, noise, and reference provenance determine whether energies can be compared.</li>
            <li>No result is displayed as calculated until the backend supplies a verified experiment record.</li>
          </ul>
          <div className="mt-6 border-t border-[#E5EEF0] pt-4 text-xs leading-5 text-[#718791]">Experiment ID: {experiment.experimentId} · Provenance: {experiment.provenance.detail}</div>
        </Panel>
      </section>
    </div>
  )
}

function MethodRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-5 py-3">
      <dt className="text-[#6B818B]">{label}</dt>
      <dd className="max-w-[60%] text-right font-medium text-[#27424E]">{value}</dd>
    </div>
  )
}
