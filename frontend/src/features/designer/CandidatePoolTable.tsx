import { Check, Plus } from 'lucide-react'
import type { BlendCandidate } from '../../types/research'
import { StatusPill } from '../../components/ui'

type CandidatePoolTableProps = {
  candidates: BlendCandidate[]
  selectedIds: Set<string>
  selectionLimit: number
  onToggle: (candidateId: string) => void
}

function originLabel(candidate: BlendCandidate): string {
  if (candidate.origin === 'position-variant' && candidate.substitution) {
    return `Variant · ${candidate.substitution.from}${candidate.substitution.position}${candidate.substitution.to}`
  }

  return candidate.origin === 'imported' ? 'Imported' : 'Entered'
}

export function CandidatePoolTable({ candidates, selectedIds, selectionLimit, onToggle }: CandidatePoolTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="research-table min-w-[42rem]">
        <thead>
          <tr>
            <th className="w-12">Select</th>
            <th>Candidate</th>
            <th>Sequence</th>
            <th>Origin</th>
            <th className="text-right">Blend status</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => {
            const isSelected = selectedIds.has(candidate.id)
            const isAtLimit = selectedIds.size >= selectionLimit
            const disableSelection = !isSelected && isAtLimit

            return (
              <tr key={candidate.id}>
                <td>
                  <input
                    aria-label={`Select ${candidate.label}`}
                    checked={isSelected}
                    className="h-4 w-4 rounded border-[#B9CDD3] text-blue-700 accent-[#087E78]"
                    disabled={disableSelection}
                    onChange={() => onToggle(candidate.id)}
                    type="checkbox"
                  />
                </td>
                <td>
                  <div className="font-semibold text-[#394957]">{candidate.label}</div>
                  <div className="mt-0.5 font-mono text-[11px] text-[#7B9099]">{candidate.id}</div>
                </td>
                <td>
                  <span className="font-mono text-xs tracking-[0.08em] text-[#394957]">{candidate.sequence}</span>
                </td>
                <td>
                  <span className="text-xs text-[#607680]">{originLabel(candidate)}</span>
                </td>
                <td className="text-right">
                  {isSelected ? (
                    <StatusPill tone="blue"><Check size={12} aria-hidden="true" /> Included</StatusPill>
                  ) : disableSelection ? (
                    <span className="text-xs text-[#8A9DA5]">Selection limit reached</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-[#6B818B]"><Plus size={12} aria-hidden="true" /> Available</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
