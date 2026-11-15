import { useEffect, useMemo, useState } from 'react'
import { artifactUrl, loadChallengeArtifacts } from './data'
import type { EnergyPoint, HardwarePreflight, ScanDocument } from './types'

type ChallengeData = {
  scan: ScanDocument
  hardware: HardwarePreflight
}

const HARTREE = 'Ha'

function formatEnergy(value: number, digits = 10): string {
  return value.toFixed(digits)
}

function formatError(value: number): string {
  return value.toExponential(3)
}

function formatDistance(value: number): string {
  return `${value.toFixed(1)} Å`
}

function humanize(value: string): string {
  return value.replaceAll('_', ' ')
}

function sampledMinimumIndex(points: EnergyPoint[]): number {
  return points.reduce(
    (minimum, point, index) =>
      point.total_molecular_energy_hartree < points[minimum].total_molecular_energy_hartree
        ? index
        : minimum,
    0,
  )
}

/** A submitted job is not evidence of a hardware energy measurement. */
function hasCompletedHardwareMeasurement(record: HardwarePreflight): boolean {
  const status = record.execution_status.trim().toLowerCase()
  const completed = status === 'completed' || status === 'complete' || status === 'done' || status.endsWith('.done')
  return (
    record.hardware_execution &&
    completed &&
    typeof record.measured_total_energy_hartree === 'number' &&
    Number.isFinite(record.measured_total_energy_hartree)
  )
}

function StatusBadge({ children, tone = 'teal' }: { children: string; tone?: 'teal' | 'amber' | 'slate' }) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>
}

function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="metric">
      <p className="metric__label">{label}</p>
      <p className="metric__value">{value}</p>
      {detail ? <p className="metric__detail">{detail}</p> : null}
    </div>
  )
}

function EnergyCurve({
  points,
  selectedIndex,
  onSelect,
}: {
  points: EnergyPoint[]
  selectedIndex: number
  onSelect: (index: number) => void
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const width = 760
  const height = 350
  const margin = { top: 26, right: 26, bottom: 54, left: 82 }
  const distances = points.map((point) => point.config.bond_distance_angstrom)
  const energies = points.flatMap((point) => [point.total_molecular_energy_hartree, point.classical_total_molecular_energy_hartree])
  const minDistance = Math.min(...distances)
  const maxDistance = Math.max(...distances)
  const rawMinEnergy = Math.min(...energies)
  const rawMaxEnergy = Math.max(...energies)
  const energyPadding = Math.max((rawMaxEnergy - rawMinEnergy) * 0.15, 0.004)
  const minEnergy = rawMinEnergy - energyPadding
  const maxEnergy = rawMaxEnergy + energyPadding
  const graphWidth = width - margin.left - margin.right
  const graphHeight = height - margin.top - margin.bottom
  const x = (distance: number) =>
    margin.left + ((distance - minDistance) / (maxDistance - minDistance || 1)) * graphWidth
  const y = (energy: number) => margin.top + ((maxEnergy - energy) / (maxEnergy - minEnergy || 1)) * graphHeight
  const vqePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(point.config.bond_distance_angstrom)} ${y(point.total_molecular_energy_hartree)}`)
    .join(' ')
  const referencePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(point.config.bond_distance_angstrom)} ${y(point.classical_total_molecular_energy_hartree)}`)
    .join(' ')
  const yTicks = Array.from({ length: 5 }, (_, index) => minEnergy + ((maxEnergy - minEnergy) * index) / 4)
  const activeIndex = hoveredIndex ?? selectedIndex
  const activePoint = points[activeIndex]

  return (
    <div className="curve-panel">
      <div className="chart-legend" aria-label="Energy curve legend">
        <span><i className="legend-line legend-line--vqe" /> VQE, StatevectorEstimator</span>
        <span><i className="legend-line legend-line--reference" /> Exact classical reference</span>
      </div>
      <div className="curve-chart-wrap">
        <svg className="curve-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="curve-title curve-desc">
          <title id="curve-title">HeH+ total molecular potential-energy curve</title>
          <desc id="curve-desc">
            Ten fixed-nuclei HeH+ calculations in STO-3G. The solid VQE line and dashed exact-reference line overlap closely.
          </desc>
          {yTicks.map((tick) => (
            <g key={tick}>
              <line className="grid-line" x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} />
              <text className="axis-label" x={margin.left - 12} y={y(tick) + 4} textAnchor="end">
                {tick.toFixed(3)}
              </text>
            </g>
          ))}
          {points.map((point) => (
            <g key={point.config.bond_distance_angstrom}>
              <line
                className="x-tick"
                x1={x(point.config.bond_distance_angstrom)}
                x2={x(point.config.bond_distance_angstrom)}
                y1={height - margin.bottom}
                y2={height - margin.bottom + 5}
              />
              <text className="axis-label" x={x(point.config.bond_distance_angstrom)} y={height - margin.bottom + 21} textAnchor="middle">
                {point.config.bond_distance_angstrom.toFixed(1)}
              </text>
            </g>
          ))}
          <line className="axis-line" x1={margin.left} x2={margin.left} y1={margin.top} y2={height - margin.bottom} />
          <line className="axis-line" x1={margin.left} x2={width - margin.right} y1={height - margin.bottom} y2={height - margin.bottom} />
          <text className="axis-title" transform={`translate(19 ${height / 2}) rotate(-90)`} textAnchor="middle">Total molecular energy (Ha)</text>
          <text className="axis-title" x={width / 2} y={height - 8} textAnchor="middle">He–H distance (Å)</text>
          <path className="reference-path" d={referencePath} />
          <path className="vqe-path" d={vqePath} />
          {points.map((point, index) => {
            const isSelected = index === selectedIndex
            const pointX = x(point.config.bond_distance_angstrom)
            const pointY = y(point.total_molecular_energy_hartree)
            return (
              <g key={`vqe-${point.config.bond_distance_angstrom}`}>
                {isSelected ? <line className="selection-line" x1={pointX} x2={pointX} y1={margin.top} y2={height - margin.bottom} /> : null}
                <circle
                  className={isSelected ? 'curve-point curve-point--selected' : 'curve-point'}
                  cx={pointX}
                  cy={pointY}
                  r={isSelected ? 6.5 : 4.5}
                  tabIndex={0}
                  role="button"
                  aria-label={`Select ${formatDistance(point.config.bond_distance_angstrom)} VQE result`}
                  onClick={() => onSelect(index)}
                  onFocus={() => setHoveredIndex(index)}
                  onBlur={() => setHoveredIndex(null)}
                  onMouseEnter={() => setHoveredIndex(index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onSelect(index)
                    }
                  }}
                />
              </g>
            )
          })}
        </svg>
        <div className="chart-readout" aria-live="polite">
          <span className="chart-readout__distance">{formatDistance(activePoint.config.bond_distance_angstrom)}</span>
          <span>VQE {formatEnergy(activePoint.total_molecular_energy_hartree, 8)} {HARTREE}</span>
          <span>|ΔE| {formatError(activePoint.absolute_total_energy_error_hartree)} {HARTREE}</span>
        </div>
      </div>
    </div>
  )
}

function MethodCard({ title, label, children }: { title: string; label: string; children: React.ReactNode }) {
  return (
    <article className="method-card">
      <span className="method-card__label">{label}</span>
      <h3>{title}</h3>
      <p>{children}</p>
    </article>
  )
}

function ChallengeDashboard({ data }: { data: ChallengeData }) {
  const points = useMemo(
    () => [...data.scan.results].sort((a, b) => a.config.bond_distance_angstrom - b.config.bond_distance_angstrom),
    [data.scan.results],
  )
  const [selectedIndex, setSelectedIndex] = useState(() => sampledMinimumIndex(points))
  const selected = points[selectedIndex] ?? points[0]
  const sampledMinimum = points[sampledMinimumIndex(points)]
  const hardwareHasRun = hasCompletedHardwareMeasurement(data.hardware)
  const hardwareEnergy = hardwareHasRun ? data.hardware.measured_total_energy_hartree : null
  const method = points[0]

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <div className="hero__orb hero__orb--one" />
        <div className="hero__orb hero__orb--two" />
        <div className="page-shell hero__content">
          <div className="eyebrow-row">
            <span className="kicker">USC × IBM Qiskit Fall Fest 2026</span>
            <StatusBadge tone="teal">Verified local simulation</StatusBadge>
          </div>
          <div className="hero-grid">
            <div>
              <p className="hero__overline">Quantum chemistry challenge</p>
              <h1 id="page-title">HeH<sup>+</sup> potential-energy curve</h1>
              <p className="hero__lede">
                A fixed-nuclei Born–Oppenheimer scan with a real Qiskit VQE calculation and a matched exact classical reference.
              </p>
              <div className="hero__tags" aria-label="Study facts">
                <span>HeH<sup>+</sup></span><span>charge +1</span><span>2 electrons</span><span>{points.length} sampled geometries</span>
              </div>
            </div>
            <aside className="hero-callout" aria-label="Scientific status">
              <span className="hero-callout__eyebrow">Interpretation</span>
              <p>These are calculated local ideal-state results — not hardware measurements and not a claim of quantum advantage.</p>
              <a href="#hardware">See hardware readiness <span aria-hidden="true">↓</span></a>
            </aside>
          </div>
        </div>
      </section>

      <div className="page-shell content-stack">
        <section className="metric-grid" aria-label="Experiment summary">
          <Metric label="Sampled lowest VQE point" value={formatDistance(sampledMinimum.config.bond_distance_angstrom)} detail={`${formatEnergy(sampledMinimum.total_molecular_energy_hartree, 8)} ${HARTREE}`} />
          <Metric label="VQE / exact agreement at 1.0 Å" value={formatError(points.find((point) => point.config.bond_distance_angstrom === 1)?.absolute_total_energy_error_hartree ?? 0)} detail={`${HARTREE}, total molecular energy`} />
          <Metric label="Logical qubits" value={String(method.qubit_count)} detail={`${method.parameter_count} variational parameters`} />
          <Metric label="Decomposed depth at 1.0 Å" value={String(points.find((point) => point.config.bond_distance_angstrom === 1)?.decomposed_circuit_depth ?? method.decomposed_circuit_depth)} detail="Before device-specific transpilation" />
        </section>

        <section className="section-card curve-section" aria-labelledby="curve-heading">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Verified result artifact</p>
              <h2 id="curve-heading">Compare the curve at each fixed geometry</h2>
            </div>
            <p>The solid VQE and dashed physical-sector exact-reference curves are nearly coincident on this ideal-state simulation.</p>
          </div>
          <EnergyCurve points={points} selectedIndex={selectedIndex} onSelect={setSelectedIndex} />
          <div className="distance-selector" aria-label="Select a sampled bond distance">
            <label htmlFor="distance-range">Inspect sampled distance <strong>{formatDistance(selected.config.bond_distance_angstrom)}</strong></label>
            <input
              id="distance-range"
              type="range"
              min="0"
              max={String(points.length - 1)}
              value={selectedIndex}
              step="1"
              onChange={(event) => setSelectedIndex(Number(event.target.value))}
            />
            <div className="distance-buttons">
              {points.map((point, index) => (
                <button
                  className={index === selectedIndex ? 'distance-button distance-button--active' : 'distance-button'}
                  key={point.config.bond_distance_angstrom}
                  type="button"
                  onClick={() => setSelectedIndex(index)}
                  aria-pressed={index === selectedIndex}
                >
                  {point.config.bond_distance_angstrom.toFixed(1)} Å
                </button>
              ))}
            </div>
          </div>
          <p className="curve-caption"><strong>Careful interpretation:</strong> {formatDistance(sampledMinimum.config.bond_distance_angstrom)} is the lowest sampled point, not a mathematically precise equilibrium geometry. The scan is sparse and uses STO-3G.</p>
        </section>

        <section className="selection-grid" aria-labelledby="selected-heading">
          <article className="section-card selected-result">
            <div className="section-heading section-heading--compact">
              <div>
                <p className="section-kicker">Selected geometry</p>
                <h2 id="selected-heading">{formatDistance(selected.config.bond_distance_angstrom)}</h2>
              </div>
              <StatusBadge tone="teal">{selected.calculation_status}</StatusBadge>
            </div>
            <div className="energy-table" role="table" aria-label="Selected energy comparison">
              <div className="energy-table__row" role="row"><span role="cell">VQE total energy</span><strong role="cell">{formatEnergy(selected.total_molecular_energy_hartree)} {HARTREE}</strong></div>
              <div className="energy-table__row" role="row"><span role="cell">Exact classical total energy</span><strong role="cell">{formatEnergy(selected.classical_total_molecular_energy_hartree)} {HARTREE}</strong></div>
              <div className="energy-table__row" role="row"><span role="cell">Absolute total-energy error</span><strong role="cell">{formatError(selected.absolute_total_energy_error_hartree)} {HARTREE}</strong></div>
              <div className="energy-table__row" role="row"><span role="cell">SLSQP objective evaluations</span><strong role="cell">{selected.optimizer_evaluations}</strong></div>
            </div>
            <div className="energy-formula">E<sub>total</sub>(R) = E<sub>electronic</sub>(R) + E<sub>nuclear repulsion</sub>(R)</div>
            <p className="formula-note">{selected.energy_convention}</p>
          </article>

          <article className="section-card selected-meta">
            <p className="section-kicker">Calculation record</p>
            <dl className="metadata-list">
              <div><dt>Basis</dt><dd>{selected.config.basis.toUpperCase()}</dd></div>
              <div><dt>Mapping</dt><dd>{selected.mapping.replace(' (no qubit reduction)', '')}</dd></div>
              <div><dt>Ansatz</dt><dd>{selected.ansatz}</dd></div>
              <div><dt>Estimator</dt><dd>{selected.estimator}</dd></div>
              <div><dt>Classical reference</dt><dd>Exact diagonalization in the physical two-electron sector</dd></div>
              <div><dt>Source</dt><dd>{humanize(data.scan.result_source)}</dd></div>
            </dl>
          </article>
        </section>

        <section className="section-card circuit-section" aria-labelledby="circuit-heading">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Actual Qiskit circuit artifact</p>
              <h2 id="circuit-heading">UCCSD circuit at 1.0 Å</h2>
            </div>
            <p>Four logical qubits; the circuit image is the verified optimized 1.0 Å calculation, not an illustrative diagram.</p>
          </div>
          <div className="circuit-grid">
            <figure className="circuit-figure">
              <img src={artifactUrl('hehplus_vqe_circuit_1.0A.png')} alt="Verified decomposed four-qubit Qiskit UCCSD circuit at 1.0 angstrom" />
              <figcaption>Exported Qiskit circuit: {points.find((point) => point.config.bond_distance_angstrom === 1)?.decomposed_circuit_depth ?? method.decomposed_circuit_depth} decomposed layers before hardware-specific transpilation.</figcaption>
            </figure>
            <div className="circuit-notes">
              <p className="circuit-notes__label">Selected-point ansatz record</p>
              <pre>{selected.circuit_text}</pre>
              <p>This compact circuit text changes with the optimized parameters selected above. The rendered artifact remains intentionally anchored to the verified 1.0 Å run.</p>
              <a className="text-link" href={artifactUrl('hehplus_vqe_circuit_1.0A.txt')} target="_blank" rel="noreferrer">Open the portable circuit text <span aria-hidden="true">↗</span></a>
            </div>
          </div>
        </section>

        <section className="method-section" aria-labelledby="method-heading">
          <div className="section-heading section-heading--on-dark">
            <div>
              <p className="section-kicker">Choice defense</p>
              <h2 id="method-heading">A deliberately small, inspectable molecular model</h2>
            </div>
            <p>Every choice is explicit in the calculation artifact so the comparison stays within one molecular model and energy convention.</p>
          </div>
          <div className="method-grid">
            <MethodCard label="Ansatz" title="Hartree–Fock + UCCSD">
              The Hartree–Fock reference encodes the physical closed-shell (1, 1) occupation. UCCSD applies particle-conserving single and double excitations, giving an expressive correlated state family for this small two-electron system. Its cost is circuit depth after decomposition.
            </MethodCard>
            <MethodCard label="Mapping" title="Jordan–Wigner">
              Jordan–Wigner directly encodes fermionic operators as qubit Pauli operators with Z strings that preserve anticommutation. It is transparent and directly supported by Qiskit Nature; the tradeoff is one qubit per spin orbital and potentially long Pauli strings.
            </MethodCard>
            <MethodCard label="Optimizer" title="SLSQP">
              SLSQP is suitable for this three-parameter, smooth, deterministic ideal-state objective. It makes convergence easy to inspect here, but finite-shot uncertainty, drift, and noise can make its estimates and stopping behavior less reliable on hardware.
            </MethodCard>
            <MethodCard label="Basis" title="STO-3G">
              The minimal STO-3G basis keeps the orbital, qubit, and circuit resource count manageable for a reproducible challenge demonstration. It is not a basis-set-converged chemical-accuracy calculation.
            </MethodCard>
          </div>
        </section>

        <section id="hardware" className="hardware-section" aria-labelledby="hardware-heading">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Hardware versus simulation</p>
              <h2 id="hardware-heading">QPU-ready workflow, no QPU result claimed</h2>
            </div>
            <StatusBadge tone={hardwareHasRun ? 'teal' : 'amber'}>{hardwareHasRun ? 'Completed hardware record' : 'Not submitted'}</StatusBadge>
          </div>
          <div className="hardware-grid">
            <article className="hardware-card hardware-card--local">
              <span>Local ideal-state VQE</span>
              <strong>{formatEnergy(data.hardware.local_ideal_vqe_total_energy_hartree)} {HARTREE}</strong>
              <p>At {formatDistance(data.hardware.bond_distance_angstrom)} with StatevectorEstimator; no shots or device noise.</p>
            </article>
            <article className="hardware-card hardware-card--classical">
              <span>Exact classical reference</span>
              <strong>{formatEnergy(data.hardware.exact_classical_total_energy_hartree)} {HARTREE}</strong>
              <p>Matched basis, charge, particle sector, geometry, and total-energy convention.</p>
            </article>
            <article className="hardware-card hardware-card--hardware">
              <span>IBM quantum hardware</span>
              <strong>{typeof hardwareEnergy !== 'number' ? 'No measured energy' : `${formatEnergy(hardwareEnergy)} ${HARTREE}`}</strong>
              <p>{hardwareHasRun ? `Completed Runtime record ${data.hardware.job_id ?? 'with an auditable result'}.` : 'A submission or queued job would not be displayed as a measurement; the checked preflight records no submitted job.'}</p>
            </article>
          </div>
          <div className="preflight-note">
            <span aria-hidden="true">◎</span>
            <p><strong>Prepared, not executed.</strong> The optional Runtime workflow binds optimized UCCSD parameters, transpiles the actual molecular circuit, applies the physical layout to the Hamiltonian observable, then adds nuclear repulsion exactly once. It only submits with an explicit backend and opt-in command.</p>
          </div>
        </section>

        <section className="section-card limitations" aria-labelledby="limitations-heading">
          <div className="section-heading section-heading--compact">
            <div>
              <p className="section-kicker">Scope and limits</p>
              <h2 id="limitations-heading">What the data supports</h2>
            </div>
          </div>
          <ul>
            {selected.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            <li>{data.hardware.submission_safety}</li>
          </ul>
        </section>

        <section className="section-card provenance" aria-labelledby="provenance-heading">
          <div className="section-heading section-heading--compact">
            <div>
              <p className="section-kicker">Reproducibility</p>
              <h2 id="provenance-heading">Verified static results, no browser-side calculation</h2>
            </div>
            <p>The dashboard reads the completed challenge scan at load time. Re-running VQE is an explicit Python-backend action, never a page-load side effect.</p>
          </div>
          <div className="provenance-grid">
            <div>
              <span>Result source</span>
              <strong>{humanize(data.scan.result_source)}</strong>
            </div>
            <div>
              <span>Generated</span>
              <strong>{new Date(data.scan.created_at_utc).toLocaleString()}</strong>
            </div>
            <div>
              <span>Qiskit / Nature</span>
              <strong>{method.package_versions.qiskit} / {method.package_versions['qiskit-nature']}</strong>
            </div>
            <div>
              <span>Algorithms / PySCF</span>
              <strong>{method.package_versions['qiskit-algorithms']} / {method.package_versions.pyscf}</strong>
            </div>
          </div>
        </section>

        <section className="artifact-links" aria-label="Download verified artifacts">
          <div>
            <p className="section-kicker">Review the source data</p>
            <h2>Static artifacts included in this standalone build</h2>
          </div>
          <div className="artifact-links__buttons">
            <a href={artifactUrl('hehplus_potential_energy_scan.json')} target="_blank" rel="noreferrer">Scan JSON <span aria-hidden="true">↗</span></a>
            <a href={artifactUrl('hehplus_potential_energy_curve.csv')} target="_blank" rel="noreferrer">Curve CSV <span aria-hidden="true">↗</span></a>
            <a href={artifactUrl('hehplus_potential_energy_curve.svg')} target="_blank" rel="noreferrer">Static curve SVG <span aria-hidden="true">↗</span></a>
            <a href={artifactUrl('submission_manifest.json')} target="_blank" rel="noreferrer">Manifest <span aria-hidden="true">↗</span></a>
          </div>
        </section>
      </div>
      <footer>
        <div className="page-shell footer-inner">
          <p>HeH<sup>+</sup> quantum chemistry challenge · verified local Qiskit calculation artifact</p>
          <p>Generated result timestamp: {new Date(data.scan.created_at_utc).toLocaleString()}</p>
        </div>
      </footer>
    </main>
  )
}

function LoadingScreen() {
  return (
    <main className="loading-screen">
      <div className="loading-mark" aria-hidden="true">HeH<sup>+</sup></div>
      <p className="kicker">Quantum chemistry challenge</p>
      <h1>Loading verified result artifacts</h1>
      <div className="loading-line" />
    </main>
  )
}

function ErrorScreen({ error }: { error: string }) {
  return (
    <main className="loading-screen">
      <div className="loading-mark loading-mark--error" aria-hidden="true">!</div>
      <p className="kicker">Artifact loading error</p>
      <h1>The standalone data could not be opened.</h1>
      <p className="error-message">{error}</p>
      <p className="error-message">Run this frontend through Vite so its checked-in static artifacts are served with the application.</p>
    </main>
  )
}

export default function App() {
  const [data, setData] = useState<ChallengeData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    loadChallengeArtifacts()
      .then((nextData) => {
        if (current) setData(nextData)
      })
      .catch((reason: unknown) => {
        if (current) setError(reason instanceof Error ? reason.message : 'An unknown artifact error occurred.')
      })
    return () => {
      current = false
    }
  }, [])

  if (error) return <ErrorScreen error={error} />
  if (!data) return <LoadingScreen />
  return <ChallengeDashboard data={data} />
}
