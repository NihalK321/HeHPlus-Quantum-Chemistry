import { lazy, Suspense } from 'react'
import { demoPairwiseProxies, demoTradeoffPoints } from '../../demo/researchDemo'

const Plot = lazy(async () => {
  const [{ default: createPlotlyComponent }, { default: Plotly }] = await Promise.all([
    import('react-plotly.js/factory'),
    import('plotly.js-cartesian-dist-min'),
  ])

  return { default: createPlotlyComponent(Plotly) }
})

function PlotLoadingState({ label }: { label: string }) {
  return <div className="grid h-[22rem] place-items-center rounded-lg border border-dashed border-[#C9D9DE] bg-[#FBFDFD] text-sm text-[#718791]">Loading {label}…</div>
}

export function TradeoffVisualizations({ chargeWeight, hydropathyWeight }: { chargeWeight: number; hydropathyWeight: number }) {
  const weightedScores = demoTradeoffPoints.map((point) => ({
    ...point,
    score: point.charge * chargeWeight + point.hydropathy * hydropathyWeight,
  }))

  const selectedLabels = weightedScores.filter((point) => point.selected).map((point) => point.id)
  const proxyLookup = new Map(demoPairwiseProxies.map((proxy) => [`${proxy.firstCandidateId}-${proxy.secondCandidateId}`, proxy.value]))
  const pairIds = ['C-01', 'C-03', 'C-05']
  const matrix = pairIds.map((rowId) => pairIds.map((columnId) => rowId === columnId ? 0 : proxyLookup.get(`${rowId}-${columnId}`) ?? proxyLookup.get(`${columnId}-${rowId}`) ?? 0))

  return (
    <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="rounded-lg border border-[#DCE7EC] bg-white p-4">
        <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[#27424E]">Demo objective trade-off scatter</h3>
            <p className="mt-1 text-xs text-[#718791]">Axes are display-only normalized objectives (a.u.), not chemical measurements.</p>
          </div>
          <span className="rounded-md bg-violet-50 px-2 py-1 text-[11px] font-semibold text-violet-800">Lazy-loaded Plotly</span>
        </div>
        <Suspense fallback={<PlotLoadingState label="interactive scatter" />}>
          <Plot
            data={[
              {
                type: 'scatter',
                mode: 'markers+text',
                name: 'Demo blend fixtures',
                x: weightedScores.map((point) => point.charge),
                y: weightedScores.map((point) => point.hydropathy),
                text: weightedScores.map((point) => point.id),
                textposition: 'top center',
                hovertemplate: '<b>%{text}</b><br>Charge target: %{x:.2f} a.u.<br>Hydropathy target: %{y:.2f} a.u.<br>Display score: %{marker.size:.2f} a.u.<extra></extra>',
                marker: {
                  color: weightedScores.map((point) => point.selected ? '#087E78' : '#93A8B0'),
                  size: weightedScores.map((point) => Math.max(12, point.score * 28)),
                  line: { color: '#FFFFFF', width: 1 },
                },
              },
            ]}
            layout={{
              autosize: true,
              height: 330,
              margin: { l: 58, r: 20, t: 16, b: 54 },
              paper_bgcolor: '#FFFFFF',
              plot_bgcolor: '#FBFDFD',
              font: { family: 'Inter, system-ui, sans-serif', color: '#36505C', size: 12 },
              showlegend: true,
              legend: { orientation: 'h', y: 1.12, x: 0 },
              xaxis: { title: { text: 'Demo charge-target objective (a.u.)', font: { size: 11 } }, gridcolor: '#E5EEF0', zeroline: false, range: [0, 0.9] },
              yaxis: { title: { text: 'Demo hydropathy-target objective (a.u.)', font: { size: 11 } }, gridcolor: '#E5EEF0', zeroline: false, range: [0, 0.9] },
              annotations: selectedLabels.map((label) => ({ text: `${label} selected`, xref: 'paper', yref: 'paper', x: 1, y: 1.1, showarrow: false, font: { size: 10, color: '#087E78' } })),
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </Suspense>
      </div>

      <div className="rounded-lg border border-[#DCE7EC] bg-white p-4">
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-[#27424E]">Demo pairwise proxy matrix</h3>
          <p className="mt-1 text-xs text-[#718791]">A display proxy is not a compatibility, binding, or synergy result.</p>
        </div>
        <Suspense fallback={<PlotLoadingState label="proxy matrix" />}>
          <Plot
            data={[{
              type: 'heatmap',
              z: matrix,
              x: pairIds,
              y: pairIds,
              colorscale: [[0, '#F2F7F7'], [1, '#087E78']],
              zmin: 0,
              zmax: 0.5,
              colorbar: { title: { text: 'Demo proxy (a.u.)', side: 'right', font: { size: 10 } }, thickness: 10 },
              hovertemplate: '%{y} × %{x}<br>Demo proxy: %{z:.2f} a.u.<extra></extra>',
            }]}
            layout={{
              autosize: true,
              height: 330,
              margin: { l: 52, r: 60, t: 16, b: 44 },
              paper_bgcolor: '#FFFFFF',
              plot_bgcolor: '#FFFFFF',
              font: { family: 'Inter, system-ui, sans-serif', color: '#36505C', size: 11 },
              xaxis: { title: { text: 'Candidate ID', font: { size: 11 } }, side: 'bottom' },
              yaxis: { title: { text: 'Candidate ID', font: { size: 11 } }, autorange: 'reversed' },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </Suspense>
      </div>
    </div>
  )
}
