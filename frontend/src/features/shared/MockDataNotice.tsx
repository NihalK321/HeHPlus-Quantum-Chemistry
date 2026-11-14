import { Info } from 'lucide-react'

type MockDataNoticeProps = {
  detail?: string
}

export function MockDataNotice({
  detail = 'Values on this screen are illustrative UI fixtures. They are not calculated chemistry, benchmark evidence, or quantum experiment results.',
}: MockDataNoticeProps) {
  return (
    <div
      className="flex items-start gap-3 rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-950"
      role="note"
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-violet-700" aria-hidden="true" />
      <span className="min-w-0">
        <span className="inline-flex rounded border border-violet-200 bg-white px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em] text-violet-800">
          Demo UI fixture
        </span>
        <span className="mt-1 block leading-6 text-violet-900/80">{detail}</span>
      </span>
    </div>
  )
}
