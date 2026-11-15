type HeHStructureDiagramProps = {
  bondDistanceAngstrom: number
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum)
}

/**
 * A geometry-only diagram. It intentionally conveys only the selected nuclear
 * separation, never an electronic density, orbital, or energy calculation.
 */
export function HeHStructureDiagram({ bondDistanceAngstrom }: HeHStructureDiagramProps) {
  const clampedDistance = clamp(bondDistanceAngstrom, 0.4, 3.5)
  const separation = 122 + ((clampedDistance - 0.4) / 3.1) * 278
  const heX = 130
  const hX = heX + separation
  const midpoint = (heX + hX) / 2

  return (
    <figure className="overflow-hidden rounded-lg border border-[#D9E0E7] bg-[#FCFEFE] p-4">
      <svg
        aria-labelledby="heh-structure-title heh-structure-description"
        className="h-auto w-full"
        role="img"
        viewBox="0 0 560 230"
      >
        <title id="heh-structure-title">HeH+ bond-distance diagram</title>
        <desc id="heh-structure-description">
          A geometry-only diagram of helium hydride with nuclei separated by the selected bond distance of {bondDistanceAngstrom.toFixed(2)} angstroms.
        </desc>
        <defs>
          <linearGradient id="heh-bond" x1="0" x2="1">
            <stop offset="0" stopColor="#087E78" stopOpacity="0.68" />
            <stop offset="1" stopColor="#8BA9B7" stopOpacity="0.68" />
          </linearGradient>
        </defs>

        <line x1={heX} x2={hX} y1="112" y2="112" stroke="url(#heh-bond)" strokeDasharray="4 5" strokeWidth="3" />
        <line x1={heX} x2={heX} y1="148" y2="170" stroke="#91A8B0" strokeWidth="1" />
        <line x1={hX} x2={hX} y1="148" y2="170" stroke="#91A8B0" strokeWidth="1" />
        <line x1={heX} x2={hX} y1="164" y2="164" stroke="#91A8B0" strokeWidth="1" />
        <path d={`M ${heX} 164 l 7 -4 v 8 Z`} fill="#91A8B0" />
        <path d={`M ${hX} 164 l -7 -4 v 8 Z`} fill="#91A8B0" />
        <text fill="#5E747F" fontFamily="Inter, system-ui, sans-serif" fontSize="12" textAnchor="middle" x={midpoint} y="185">
          {bondDistanceAngstrom.toFixed(2)} Å
        </text>

        <circle cx={heX} cy="112" fill="#0B7D77" r="38" />
        <circle cx={heX - 12} cy="98" fill="#42A39E" opacity="0.42" r="11" />
        <text fill="#FFFFFF" fontFamily="Inter, system-ui, sans-serif" fontSize="18" fontWeight="700" textAnchor="middle" x={heX} y="118">He</text>
        <text fill="#48636D" fontFamily="Inter, system-ui, sans-serif" fontSize="11" textAnchor="middle" x={heX} y="48">helium nucleus</text>

        <circle cx={hX} cy="112" fill="#607D8B" r="27" />
        <circle cx={hX - 8} cy="102" fill="#A9C1CA" opacity="0.52" r="8" />
        <text fill="#FFFFFF" fontFamily="Inter, system-ui, sans-serif" fontSize="17" fontWeight="700" textAnchor="middle" x={hX} y="118">H</text>
        <text fill="#48636D" fontFamily="Inter, system-ui, sans-serif" fontSize="11" textAnchor="middle" x={hX} y="48">hydrogen nucleus</text>

        <text fill="#6A818B" fontFamily="Inter, system-ui, sans-serif" fontSize="11" x="18" y="212">
          Structural diagram only — it does not depict an electronic state, orbital, or calculated energy.
        </text>
      </svg>
    </figure>
  )
}
