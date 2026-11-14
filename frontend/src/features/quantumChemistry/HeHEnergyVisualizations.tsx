import { ChartNoAxesCombined } from 'lucide-react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState } from '../../components/ui'
import type { HeHEnergyPoint, HeHExperiment, VqeConvergencePoint } from '../../types/quantumChemistry'

function formatHartree(value: number | null): string {
  return value === null ? 'Unavailable' : `${value.toFixed(8)} Ha`
}

function energyAxisLabel(convention: HeHExperiment['energyConvention']): string {
  if (convention === 'electronic_energy') return 'Electronic energy (Ha)'
  if (convention === 'total_molecular_energy') return 'Total molecular energy (Ha)'
  return 'Energy (Ha; convention unspecified)'
}

export function PotentialEnergySurfaceChart({
  points,
  energyConvention,
}: {
  points: HeHEnergyPoint[]
  energyConvention: HeHExperiment['energyConvention']
}) {
  const plottedPoints = points
    .filter((point) => point.vqeEnergyHartree !== null || point.referenceEnergyHartree !== null)
    .map((point) => ({
      distance: point.bondDistanceAngstrom,
      vqe: point.vqeEnergyHartree,
      reference: point.referenceEnergyHartree,
      error: point.absoluteErrorHartree,
    }))

  if (plottedPoints.length === 0) {
    return (
      <EmptyState
        detail="No verified HeH+ energy points have been supplied. This chart will plot VQE and classical-reference energies in Hartrees when a completed experiment is available."
        title="Potential-energy data unavailable"
      />
    )
  }

  return (
    <div className="h-[22rem]" role="img" aria-label={`${energyAxisLabel(energyConvention)} curve for HeH+ with VQE and classical-reference energies`}>
      <ResponsiveContainer height="100%" width="100%">
        <LineChart data={plottedPoints} margin={{ top: 14, right: 18, left: 20, bottom: 16 }}>
          <CartesianGrid stroke="#E5EEF0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="distance"
            label={{ value: 'He–H bond distance (Å)', position: 'insideBottom', offset: -6, fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            label={{ value: energyAxisLabel(energyConvention), angle: -90, position: 'insideLeft', fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickFormatter={(value: number) => value.toFixed(4)}
            tickLine={false}
            width={72}
          />
          <Tooltip
            contentStyle={{ border: '1px solid #DCE7EC', borderRadius: 8, boxShadow: '0 8px 18px rgb(23 43 58 / 8%)', fontSize: 12 }}
            formatter={(value, name) => [formatHartree(typeof value === 'number' ? value : null), name]}
            labelFormatter={(label) => `Bond distance: ${Number(label).toFixed(3)} Å`}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Line connectNulls dataKey="vqe" dot={{ r: 3, fill: '#087E78' }} name="VQE energy" stroke="#087E78" strokeWidth={2.25} type="monotone" />
          <Line connectNulls dataKey="reference" dot={{ r: 3, fill: '#657B85' }} name="Classical reference" stroke="#657B85" strokeDasharray="5 4" strokeWidth={2} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function EnergyErrorChart({ points }: { points: HeHEnergyPoint[] }) {
  const plottedPoints = points
    .filter((point) => point.absoluteErrorHartree !== null)
    .map((point) => ({
      distance: point.bondDistanceAngstrom,
      absoluteError: point.absoluteErrorHartree,
      uncertainty: point.vqeEnergyUncertaintyHartree,
    }))

  if (plottedPoints.length === 0) {
    return (
      <EmptyState
        detail="No verified error values have been supplied. Absolute error can be interpreted only where VQE and a comparable classical reference use the stated energy convention."
        title="Energy-error data unavailable"
      />
    )
  }

  return (
    <div className="h-[19rem]" role="img" aria-label="Absolute VQE energy error by HeH+ bond distance">
      <ResponsiveContainer height="100%" width="100%">
        <LineChart data={plottedPoints} margin={{ top: 14, right: 18, left: 20, bottom: 16 }}>
          <CartesianGrid stroke="#E5EEF0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="distance"
            label={{ value: 'He–H bond distance (Å)', position: 'insideBottom', offset: -6, fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            label={{ value: 'Absolute error (Ha)', angle: -90, position: 'insideLeft', fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickFormatter={(value: number) => value.toExponential(1)}
            tickLine={false}
            width={72}
          />
          <Tooltip
            contentStyle={{ border: '1px solid #DCE7EC', borderRadius: 8, boxShadow: '0 8px 18px rgb(23 43 58 / 8%)', fontSize: 12 }}
            formatter={(value, name) => [formatHartree(typeof value === 'number' ? value : null), name === 'absoluteError' ? 'Absolute error' : 'VQE uncertainty']}
            labelFormatter={(label) => `Bond distance: ${Number(label).toFixed(3)} Å`}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Line connectNulls dataKey="absoluteError" dot={{ r: 3, fill: '#C66B22' }} name="Absolute error" stroke="#C66B22" strokeWidth={2.25} type="monotone" />
          <Line connectNulls dataKey="uncertainty" dot={{ r: 3, fill: '#8A98A1' }} name="VQE uncertainty" stroke="#8A98A1" strokeDasharray="4 4" strokeWidth={1.75} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function VqeConvergenceChart({ points }: { points: VqeConvergencePoint[] }) {
  const plottedPoints = points.filter((point) => point.estimatedEnergyHartree !== null || point.referenceEnergyHartree !== null)

  if (plottedPoints.length === 0) {
    return (
      <EmptyState
        detail="A completed VQE run can provide iteration-by-iteration estimated energy and the comparable classical-reference value for this bond distance."
        title="Convergence history unavailable"
      />
    )
  }

  return (
    <div className="h-[19rem]" role="img" aria-label="VQE optimization convergence chart">
      <ResponsiveContainer height="100%" width="100%">
        <LineChart data={plottedPoints} margin={{ top: 14, right: 18, left: 20, bottom: 16 }}>
          <CartesianGrid stroke="#E5EEF0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="iteration"
            label={{ value: 'Optimizer iteration', position: 'insideBottom', offset: -6, fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            label={{ value: 'Estimated energy (Ha)', angle: -90, position: 'insideLeft', fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickFormatter={(value: number) => value.toFixed(4)}
            tickLine={false}
            width={72}
          />
          <Tooltip
            contentStyle={{ border: '1px solid #DCE7EC', borderRadius: 8, boxShadow: '0 8px 18px rgb(23 43 58 / 8%)', fontSize: 12 }}
            formatter={(value, name) => [formatHartree(typeof value === 'number' ? value : null), name]}
            labelFormatter={(label) => `Iteration ${label}`}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Line connectNulls dataKey="estimatedEnergyHartree" dot={{ r: 3, fill: '#087E78' }} name="VQE estimate" stroke="#087E78" strokeWidth={2.25} type="monotone" />
          <Line connectNulls dataKey="referenceEnergyHartree" dot={false} name="Classical reference" stroke="#657B85" strokeDasharray="5 4" strokeWidth={2} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ChartContextNote({ children }: { children: string }) {
  return (
    <div className="mt-4 flex items-start gap-2 border-t border-[#E5EEF0] pt-3 text-xs leading-5 text-[#6B818B]">
      <ChartNoAxesCombined className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}
