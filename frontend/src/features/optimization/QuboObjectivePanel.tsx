import { Braces, Sigma } from 'lucide-react'

export function QuboObjectivePanel({ gamma, lambda, blendSize }: { gamma: number; lambda: number; blendSize: number }) {
  return (
    <div className="rounded-lg border border-[#DCE7EC] bg-[#FBFDFD] p-4">
      <div className="flex items-start gap-3">
        <span className="rounded-md bg-[#EAF5F4] p-2 text-teal-700"><Sigma size={16} aria-hidden="true" /></span>
        <div>
          <p className="text-sm font-semibold text-[#27424E]">Blend-selection objective</p>
          <p className="mt-1 text-xs leading-5 text-[#657B85]">A presentation of the proposed model form only. Coefficients and scores await chemistry and quantum-team agreement.</p>
        </div>
      </div>
      <div className="mt-4 overflow-x-auto rounded-md border border-[#E1ECEE] bg-white px-3 py-3 font-mono text-sm text-[#27424E]">
        E(x) = −Σ Sᵢxᵢ + γΣ Pᵢⱼxᵢxⱼ + λ(Σxᵢ − k)²
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <div><dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#718791]">γ pairwise proxy weight</dt><dd className="mt-1 font-mono text-sm text-[#203B46]">{gamma.toFixed(2)} · UI input</dd></div>
        <div><dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#718791]">λ cardinality penalty</dt><dd className="mt-1 font-mono text-sm text-[#203B46]">{lambda.toFixed(2)} · UI input</dd></div>
        <div><dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#718791]">k selected candidates</dt><dd className="mt-1 font-mono text-sm text-[#203B46]">{blendSize}</dd></div>
      </dl>
      <div className="mt-4 flex items-start gap-2 border-t border-[#E6EFF1] pt-3 text-xs leading-5 text-[#657B85]">
        <Braces className="mt-0.5 shrink-0 text-[#087E78]" size={14} aria-hidden="true" />
        <p>Each binary variable represents whether an entire peptide candidate is selected. Amino-acid substitutions belong upstream in candidate generation.</p>
      </div>
    </div>
  )
}
