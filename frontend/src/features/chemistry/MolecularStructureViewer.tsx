import { Rotate3D, RotateCcw, Upload, ZoomIn } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { Button, EmptyState, StatusPill } from '../../components/ui'

type StructureFormat = 'pdb' | 'sdf' | 'mol'
type Representation = 'stick' | 'sphere' | 'cartoon'

function formatFromFile(file: File): StructureFormat | null {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (extension === 'pdb') return 'pdb'
  if (extension === 'sdf') return 'sdf'
  if (extension === 'mol') return 'mol'

  return null
}

function atomDescription(atom: Record<string, unknown>): string {
  const atomName = typeof atom.atom === 'string' ? atom.atom : 'Atom'
  const residue = typeof atom.resn === 'string' ? atom.resn : 'unknown residue'
  const residueIndex = atom.resi === undefined ? '' : ` ${String(atom.resi)}`
  const chain = typeof atom.chain === 'string' && atom.chain ? `, chain ${atom.chain}` : ''

  return `${atomName} · ${residue}${residueIndex}${chain}`
}

export function MolecularStructureViewer() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<import('3dmol').GLViewer | null>(null)
  const [structureText, setStructureText] = useState<string | null>(null)
  const [format, setFormat] = useState<StructureFormat>('pdb')
  const [fileName, setFileName] = useState<string | null>(null)
  const [representation, setRepresentation] = useState<Representation>('stick')
  const [viewerError, setViewerError] = useState<string | null>(null)
  const [selectedAtom, setSelectedAtom] = useState<string | null>(null)

  useEffect(() => {
    const container = containerRef.current

    if (!container || !structureText) return

    const viewerContainer = container

    let cancelled = false
    let resizeObserver: ResizeObserver | undefined

    async function renderStructure() {
      try {
        setViewerError(null)
        const $3Dmol = await import('3dmol')

        if (cancelled || !containerRef.current) return

        viewerContainer.replaceChildren()
        const viewer = $3Dmol.createViewer(viewerContainer, {
          backgroundColor: '#f8fafc',
          antialias: true,
        })

        viewerRef.current = viewer
        viewer.addModel(structureText, format)

        if (representation === 'sphere') {
          viewer.setStyle({}, { sphere: { scale: 0.3, colorscheme: 'Jmol' } })
        } else if (representation === 'cartoon') {
          viewer.setStyle({}, { cartoon: { color: 'spectrum' } })
          viewer.setStyle({}, { stick: { radius: 0.12, colorscheme: 'Jmol' } })
        } else {
          viewer.setStyle({}, { stick: { radius: 0.18, colorscheme: 'Jmol' } })
        }

        viewer.setClickable({}, true, (atom: Record<string, unknown>) => {
          setSelectedAtom(atomDescription(atom))
        })
        viewer.zoomTo()
        viewer.render()

        resizeObserver = new ResizeObserver(() => {
          viewer.resize()
          viewer.render()
        })
        resizeObserver.observe(viewerContainer)
      } catch (error) {
        viewerRef.current = null
        setViewerError(
          error instanceof Error
            ? `The structure could not be rendered: ${error.message}`
            : 'The browser could not initialize the WebGL molecular viewer.',
        )
      }
    }

    void renderStructure()

    return () => {
      cancelled = true
      resizeObserver?.disconnect()
      viewerRef.current?.clear()
      viewerRef.current = null
      viewerContainer.replaceChildren()
    }
  }, [format, representation, structureText])

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]

    if (!file) return

    const detectedFormat = formatFromFile(file)

    if (!detectedFormat) {
      setStructureText(null)
      setFileName(null)
      setViewerError('Choose a .pdb, .sdf, or .mol structure file. Files remain in this browser session and are not uploaded.')
      return
    }

    try {
      const text = await file.text()

      if (!text.trim()) {
        throw new Error('The selected file is empty.')
      }

      setFormat(detectedFormat)
      setFileName(file.name)
      setSelectedAtom(null)
      setViewerError(null)
      setStructureText(text)
    } catch (error) {
      setStructureText(null)
      setFileName(null)
      setViewerError(error instanceof Error ? error.message : 'The selected structure file could not be read.')
    }
  }

  function resetView() {
    viewerRef.current?.zoomTo()
    viewerRef.current?.render()
    setSelectedAtom(null)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-semibold text-[#27424E]">Interactive structure viewer</p>
          <p className="mt-1 text-xs leading-5 text-[#6B818B]">Load a local PDB, SDF, or MOL file to inspect its supplied atomic coordinates. No model is generated by PepperQ.</p>
        </div>
        <StatusPill tone={structureText ? 'teal' : 'amber'}>{structureText ? 'Local structure loaded' : 'No structure loaded'}</StatusPill>
      </div>

      <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-[#B9CDD3] bg-[#FBFDFD] px-4 py-3 text-sm font-semibold text-[#31515C] transition hover:border-teal-600 hover:bg-teal-50">
        <Upload className="h-4 w-4" aria-hidden="true" />
        <span>{fileName ? `Replace ${fileName}` : 'Choose a local PDB, SDF, or MOL file'}</span>
        <input accept=".pdb,.sdf,.mol" className="sr-only" onChange={handleFile} type="file" />
      </label>

      {viewerError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900" role="alert">
          {viewerError}
        </div>
      )}

      {structureText ? (
        <>
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-[#DCE7EC] bg-[#FBFDFD] p-2">
            <span className="px-2 text-xs font-semibold text-[#5D747E]">Representation</span>
            {(['stick', 'sphere', 'cartoon'] as const).map((option) => (
              <button
                className={`rounded-md px-2.5 py-1.5 text-xs font-semibold capitalize transition ${
                  representation === option ? 'bg-teal-700 text-white' : 'text-[#47616B] hover:bg-teal-50 hover:text-teal-800'
                }`}
                key={option}
                onClick={() => setRepresentation(option)}
                type="button"
              >
                {option}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-1">
              <Button className="px-2.5 py-1.5 text-xs" onClick={resetView} variant="ghost">
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                Reset view
              </Button>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-lg border border-[#DCE7EC] bg-[#F8FAFC]">
            <div className="h-[24rem] w-full" ref={containerRef} />
            <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-[#DCE7EC] bg-white/95 px-2.5 py-1.5 text-[11px] text-[#5D747E] shadow-sm">
              <span className="inline-flex items-center gap-1"><Rotate3D className="h-3.5 w-3.5" aria-hidden="true" /> Drag to rotate</span>
              <span className="mx-2 text-[#B4C4C9]">·</span>
              <span className="inline-flex items-center gap-1"><ZoomIn className="h-3.5 w-3.5" aria-hidden="true" /> Scroll to zoom</span>
            </div>
          </div>

          <div className="rounded-md border border-[#DCE7EC] bg-[#FBFDFD] px-3 py-2 text-xs leading-5 text-[#5D747E]">
            {selectedAtom ? `Selected atom: ${selectedAtom}` : 'Select an atom in the loaded structure to inspect the residue and chain values supplied by the file.'}
          </div>
        </>
      ) : (
        <EmptyState
          detail="No valid molecular structure is available in this repository. Load a research-approved PDB, SDF, or MOL file to enable the viewer; a visual model will not be invented from sequence text."
          title="Structure data is optional and currently unavailable"
        />
      )}
    </div>
  )
}
