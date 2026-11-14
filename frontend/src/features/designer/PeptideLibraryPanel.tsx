import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Check, ChevronLeft, ChevronRight, Database, ExternalLink, Info, LoaderCircle, Plus, Search } from 'lucide-react'
import { isApiClientError } from '../../api/client'
import { Button, EmptyState, Panel, StatusPill } from '../../components/ui'
import { peptideLibraryService } from '../../services/peptideLibrary'
import { toSelectedPeptideCandidate } from '../../types/peptideLibrary'
import type { PeptideAnnotation, PeptideLibraryRecord, PeptideLibraryStats, PeptideSearchParams, PeptideSearchResponse, PeptideSourceReference, SelectedPeptideCandidate } from '../../types/peptideLibrary'

type PeptideLibraryPanelProps = {
  selectedIds: ReadonlySet<string>
  onToggle: (candidate: SelectedPeptideCandidate) => void
  maxSelections: number
}

type DraftFilters = {
  search: string
  source: string
  minLength: string
  maxLength: string
  annotation: string
}

const initialFilters: DraftFilters = { search: '', source: '', minLength: '', maxLength: '', annotation: '' }
const pageSize = 20

function formatError(error: unknown): string {
  if (isApiClientError(error)) return error.message
  return error instanceof Error ? error.message : 'The local peptide-library service could not be reached.'
}

function optionalPositiveInteger(value: string): number | undefined {
  if (!value.trim()) return undefined
  const numberValue = Number(value)
  return Number.isInteger(numberValue) && numberValue > 0 ? numberValue : undefined
}

function sequencePreview(sequence: string): string {
  return sequence.length > 36 ? `${sequence.slice(0, 36)}...` : sequence
}

function primarySource(record: PeptideLibraryRecord): PeptideSourceReference | undefined {
  return record.sourceReferences[0]
}

function sourceLabel(reference: PeptideSourceReference): string {
  return `${reference.sourceDatabase} · ${reference.sourceAccession}`
}

function annotationLabel(annotation: PeptideAnnotation): string {
  const type = typeof annotation.type === 'string' ? annotation.type : ''
  const description = typeof annotation.description === 'string' ? annotation.description : ''
  return [type, description].filter(Boolean).join(': ') || 'Source annotation'
}

export function PeptideLibraryPanel({ selectedIds, onToggle, maxSelections }: PeptideLibraryPanelProps) {
  const [draftFilters, setDraftFilters] = useState<DraftFilters>(initialFilters)
  const [activeParams, setActiveParams] = useState<PeptideSearchParams>({ page: 1, pageSize })
  const [results, setResults] = useState<PeptideSearchResponse | null>(null)
  const [stats, setStats] = useState<PeptideLibraryStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingStats, setIsLoadingStats] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<PeptideLibraryRecord | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)

  const sources = useMemo(() => Object.entries(stats?.bySource ?? {}).sort(([first], [second]) => first.localeCompare(second)), [stats])
  const currentPage = results?.page ?? activeParams.page ?? 1
  const responsePageSize = results?.pageSize ?? pageSize
  const totalPages = Math.max(1, Math.ceil((results?.total ?? 0) / responsePageSize))

  useEffect(() => {
    let current = true

    void peptideLibraryService.search(activeParams)
      .then((response) => {
        if (current) setResults(response)
      })
      .catch((requestError: unknown) => {
        if (current) setError(formatError(requestError))
      })
      .finally(() => {
        if (current) setIsLoading(false)
      })

    return () => {
      current = false
    }
  }, [activeParams])

  useEffect(() => {
    let current = true

    void peptideLibraryService.stats()
      .then((response) => {
        if (current) setStats(response)
      })
      .catch(() => {
        // Keep a genuine request failure separate from scientific records; no
        // demo peptide records are ever substituted here.
        if (current) setStats(null)
      })
      .finally(() => {
        if (current) setIsLoadingStats(false)
      })

    return () => {
      current = false
    }
  }, [])

  function applyFilters() {
    setDetail(null)
    setDetailError(null)
    setIsLoading(true)
    setError(null)
    setActiveParams({
      search: draftFilters.search,
      source: draftFilters.source,
      minLength: optionalPositiveInteger(draftFilters.minLength),
      maxLength: optionalPositiveInteger(draftFilters.maxLength),
      annotation: draftFilters.annotation,
      page: 1,
      pageSize,
    })
  }

  function changePage(page: number) {
    setDetail(null)
    setDetailError(null)
    setIsLoading(true)
    setError(null)
    setActiveParams((current) => ({ ...current, page }))
  }

  async function requestDetails(record: PeptideLibraryRecord) {
    if (detail?.id === record.id) {
      setDetail(null)
      setDetailError(null)
      return
    }

    setIsLoadingDetail(true)
    setDetailError(null)
    try {
      setDetail(await peptideLibraryService.get(record.id))
    } catch (requestError) {
      // The already retrieved local-search record remains a truthful fallback.
      setDetail(record)
      setDetailError(formatError(requestError))
    } finally {
      setIsLoadingDetail(false)
    }
  }

  const totalLabel = results ? `${results.total.toLocaleString()} matching record${results.total === 1 ? '' : 's'}` : 'Awaiting library response'

  return (
    <Panel className="overflow-hidden" aria-labelledby="peptide-library-heading">
      <div className="border-b border-[#D9E0E7] px-5 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="rounded-lg bg-blue-50 p-2 text-blue-700"><Database size={18} aria-hidden="true" /></span>
            <div>
              <p className="research-eyebrow">Imported scientific records</p>
              <h2 className="mt-1 text-lg font-semibold text-[#28323C]" id="peptide-library-heading">Peptide library</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-[#657B85]">Search locally imported source records. Only standard-residue sequences are selectable for a future QAOA candidate pool; records needing special handling remain visible with their provenance.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill tone={isLoadingStats ? 'slate' : stats ? 'blue' : 'amber'}>{isLoadingStats ? 'Loading library status' : stats ? `${stats.totalPeptides.toLocaleString()} imported peptides` : 'Library status unavailable'}</StatusPill>
            <StatusPill tone={selectedIds.size === maxSelections ? 'blue' : 'slate'}>{selectedIds.size} of {maxSelections} future candidates</StatusPill>
          </div>
        </div>

        <form className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-[1.4fr_0.85fr_0.55fr_0.55fr_0.85fr_auto]" onSubmit={(event) => { event.preventDefault(); applyFilters() }}>
          <label className="research-label">Name or sequence
            <span className="relative mt-1.5 block"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#78909A]" aria-hidden="true" /><input className="research-input pl-9" onChange={(event) => setDraftFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Search an imported name or sequence" value={draftFilters.search} /></span>
          </label>
          <label className="research-label">Source
            <select className="research-select mt-1.5" onChange={(event) => setDraftFilters((current) => ({ ...current, source: event.target.value }))} value={draftFilters.source}><option value="">All imported sources</option>{sources.map(([source, count]) => <option key={source} value={source}>{source} ({count.toLocaleString()})</option>)}</select>
          </label>
          <label className="research-label">Min length<input className="research-input mt-1.5" inputMode="numeric" min="1" onChange={(event) => setDraftFilters((current) => ({ ...current, minLength: event.target.value }))} placeholder="Any" type="number" value={draftFilters.minLength} /></label>
          <label className="research-label">Max length<input className="research-input mt-1.5" inputMode="numeric" min="1" onChange={(event) => setDraftFilters((current) => ({ ...current, maxLength: event.target.value }))} placeholder="Any" type="number" value={draftFilters.maxLength} /></label>
          <label className="research-label">Annotation<input className="research-input mt-1.5" onChange={(event) => setDraftFilters((current) => ({ ...current, annotation: event.target.value }))} placeholder="Feature or category" value={draftFilters.annotation} /></label>
          <div className="flex items-end"><Button className="w-full" type="submit"><Search className="h-4 w-4" aria-hidden="true" /> Search</Button></div>
        </form>

        {stats && <p className="mt-3 text-xs leading-5 text-[#718791]" role="status">{stats.totalSourceRecords.toLocaleString()} source records · {stats.withStructures.toLocaleString()} with explicit structure references · {stats.withExperimentalAnnotations.toLocaleString()} with experimental annotations.</p>}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E7EFF1] bg-[#F8FAFC] px-5 py-3"><p className="text-sm font-medium text-[#36505C]">{totalLabel}</p>{isLoading && <span className="inline-flex items-center gap-2 text-xs text-[#657B85]"><LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading imported records</span>}</div>

      {error && <div className="m-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950" role="alert"><div className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /><div><p className="font-semibold">Library search unavailable</p><p className="mt-1 leading-6">{error}</p><p className="mt-1 text-xs leading-5">No demonstration peptide records are substituted for an unavailable source.</p></div></div><Button className="mt-3" onClick={() => { setIsLoading(true); setError(null); setActiveParams({ ...activeParams }) }} variant="secondary">Retry search</Button></div>}

      {!isLoading && !error && results?.items.length === 0 && <div className="p-5"><EmptyState detail="No locally imported peptide record matches these filters. Change the search, import additional verified records, or confirm that the local database has been populated." title="No peptide records found" /></div>}

      {results && results.items.length > 0 && <div className="overflow-x-auto p-2 sm:p-3"><table className="research-table min-w-[64rem]"><thead><tr><th className="w-20">Select</th><th>Peptide</th><th>Sequence</th><th>Length</th><th>Primary source</th><th>Validation</th><th className="text-right">Details</th></tr></thead><tbody>{results.items.map((record) => <LibraryRow detailId={detail?.id} key={record.id} maxSelections={maxSelections} onDetails={() => { void requestDetails(record) }} onToggle={onToggle} record={record} selectedIds={selectedIds} />)}</tbody></table></div>}

      {detail && <PeptideDetailPanel error={detailError} isLoading={isLoadingDetail} onClose={() => setDetail(null)} record={detail} />}

      {results && results.total > 0 && <div className="flex items-center justify-between gap-3 border-t border-[#E7EFF1] px-5 py-4"><p className="text-xs text-[#6B818B]">Page {currentPage} of {totalPages}</p><div className="flex gap-2"><Button disabled={currentPage <= 1 || isLoading} onClick={() => changePage(currentPage - 1)} variant="secondary"><ChevronLeft className="h-4 w-4" aria-hidden="true" /> Previous</Button><Button disabled={currentPage >= totalPages || isLoading} onClick={() => changePage(currentPage + 1)} variant="secondary">Next <ChevronRight className="h-4 w-4" aria-hidden="true" /></Button></div></div>}
    </Panel>
  )
}

function LibraryRow({ record, selectedIds, maxSelections, onToggle, onDetails, detailId }: { record: PeptideLibraryRecord; selectedIds: ReadonlySet<string>; maxSelections: number; onToggle: (candidate: SelectedPeptideCandidate) => void; onDetails: () => void; detailId: string | undefined }) {
  const selected = selectedIds.has(record.id)
  const atLimit = selectedIds.size >= maxSelections && !selected
  const source = primarySource(record)
  const isSelectable = record.selectableForOptimization && !atLimit

  return <tr><td><Button aria-label={`${selected ? 'Remove' : 'Add'} ${record.name}`} className="min-w-20 px-2.5 py-1.5 text-xs" disabled={!selected && !isSelectable} onClick={() => onToggle(toSelectedPeptideCandidate(record))} variant={selected ? 'secondary' : 'primary'}>{selected ? <><Check className="h-3.5 w-3.5" aria-hidden="true" /> Added</> : <><Plus className="h-3.5 w-3.5" aria-hidden="true" /> Add</>}</Button></td><td><div className="font-semibold text-[#394957]">{record.name}</div><div className="mt-0.5 font-mono text-[11px] text-[#7B9099]">{record.id}</div></td><td><span className="font-mono text-xs tracking-[0.07em] text-[#394957]" title={record.sequence}>{sequencePreview(record.sequence)}</span></td><td>{record.sequenceLength}</td><td>{source ? <div><span className="font-medium text-[#36505C]">{sourceLabel(source)}</span>{source.sourceUrl && <a className="ml-1 inline-flex align-middle text-blue-700 hover:text-blue-900" href={source.sourceUrl} rel="noreferrer" target="_blank" title={`Open ${sourceLabel(source)}`}><ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /></a>}</div> : <span className="text-[#8A9DA5]">Unavailable</span>}</td><td>{record.selectableForOptimization ? <StatusPill tone="blue">Standard residues</StatusPill> : <StatusPill tone="amber">Special handling</StatusPill>}</td><td className="text-right"><Button className="px-2.5 py-1.5 text-xs" onClick={onDetails} variant="ghost">{detailId === record.id ? 'Close' : 'View'}</Button></td></tr>
}

function PeptideDetailPanel({ record, isLoading, error, onClose }: { record: PeptideLibraryRecord; isLoading: boolean; error: string | null; onClose: () => void }) {
  return <aside className="border-t border-[#D9E0E7] bg-[#F8FAFC] p-5" aria-labelledby="peptide-detail-heading"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="research-eyebrow">Record provenance</p><h3 className="mt-1 text-base font-semibold text-[#28323C]" id="peptide-detail-heading">{record.name}</h3></div><Button onClick={onClose} variant="ghost">Close details</Button></div>{isLoading && <p className="mt-3 inline-flex items-center gap-2 text-sm text-[#657B85]"><LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading complete record</p>}{error && <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950"><Info className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" /> The detail endpoint was unavailable, so the currently loaded search result is shown. {error}</p>}<div className="mt-4 grid gap-4 lg:grid-cols-[0.75fr_1.25fr]"><div className="rounded-lg border border-[#D9E0E7] bg-white p-4"><p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6B818B]">Sequence</p><p className="mt-2 break-all font-mono text-sm tracking-[0.09em] text-[#394957]">{record.sequence}</p><p className="mt-3 text-xs leading-5 text-[#657B85]">{record.sequenceLength} residues · {record.selectableForOptimization ? 'standard residue sequence' : `special handling required: ${record.nonstandardResidues.join(', ') || 'source validation flag'}`}</p></div><div className="space-y-3">{record.sourceReferences.map((reference) => <SourceReferenceCard key={reference.id} reference={reference} />)}</div></div></aside>
}

function SourceReferenceCard({ reference }: { reference: PeptideSourceReference }) {
  const coordinates = reference.peptideFeatureCoordinates

  return <article className="rounded-lg border border-[#D9E0E7] bg-white p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold text-[#394957]">{sourceLabel(reference)}</p><p className="mt-1 text-xs leading-5 text-[#6B818B]">{reference.evidenceType ?? 'Evidence type unavailable'}{reference.organism ? ` · ${reference.organism}` : ''}</p></div>{reference.sourceUrl && <a className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:text-blue-900" href={reference.sourceUrl} rel="noreferrer" target="_blank">Open source <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /></a>}</div>{reference.description && <p className="mt-3 text-sm leading-6 text-[#5E747F]">{reference.description}</p>}<dl className="mt-3 grid gap-3 text-xs text-[#657B85] sm:grid-cols-2"><div><dt className="font-semibold text-[#65717D]">Parent / feature</dt><dd className="mt-1">{reference.parentProteinAccession ?? 'Not applicable'}{coordinates ? ` · ${coordinates.start}-${coordinates.end} (${coordinates.coordinateSystem})` : ''}</dd></div><div><dt className="font-semibold text-[#65717D]">Source version</dt><dd className="mt-1">{reference.sourceVersion ?? 'Unavailable'}{reference.retrievalTimestamp ? ` · retrieved ${reference.retrievalTimestamp}` : ''}</dd></div></dl><AnnotationList label="Annotations" values={reference.annotations} /><AnnotationList label="Modifications" values={reference.modifications} />{reference.structureReferences.length > 0 && <div className="mt-3"><p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6B818B]">Explicit structure references</p><div className="mt-1 flex flex-wrap gap-2">{reference.structureReferences.map((structure) => <a className="rounded-md border border-[#C9D9DE] bg-white px-2 py-1 text-xs font-medium text-blue-700 hover:border-blue-600 hover:bg-blue-50" href={structure.url} key={`${structure.source ?? 'source'}-${structure.identifier}`} rel="noreferrer" target="_blank">{structure.identifier}{structure.method ? ` · ${structure.method}` : ''}</a>)}</div></div>}{reference.availableExperimentalProperties && <p className="mt-3 text-xs leading-5 text-[#657B85]">Experimental annotations retain their source context; they are not converted into PepperQ chemistry scores.</p>}</article>
}

function AnnotationList({ label, values }: { label: string; values: PeptideAnnotation[] }) {
  if (values.length === 0) return null
  return <div className="mt-3"><p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6B818B]">{label}</p><ul className="mt-1 space-y-1 text-xs leading-5 text-[#5E747F]">{values.map((value, index) => <li key={`${label}-${index}`}>{annotationLabel(value)}</li>)}</ul></div>
}
