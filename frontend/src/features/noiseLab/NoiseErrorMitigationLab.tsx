import { AlertTriangle, BarChart3, Cpu, ShieldCheck } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { demoNoiseComparison, demoProvenance } from '../../demo/researchDemo'
import { Button, Panel, SectionHeading, StatusPill } from '../../components/ui'
import { MockDataNotice } from '../shared/MockDataNotice'

const barColors = ['#8BA0AA', '#C9853C', '#087E78']

export function NoiseErrorMitigationLab() {
  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Optional experiment workspace"
        title="Noise and error mitigation lab"
        description="A stretch workspace for documenting noise assumptions and comparing recorded outcomes only after the core blend workflow is validated."
        action={<StatusPill tone="amber">No experiment connected</StatusPill>}
      />

      <MockDataNotice detail="All chart values on this page are centralized DEMO UI fixtures. They are not simulator, hardware, noise, mitigation, or uncertainty measurements." />

      <section className="grid gap-5 xl:grid-cols-[0.78fr_1.22fr]">
        <Panel className="p-5" aria-labelledby="noise-settings-heading">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-[#F5F7F8] text-[#52707B]"><Cpu size={18} /></span>
            <div><p className="research-eyebrow">Experiment declaration</p><h2 id="noise-settings-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Required settings</h2></div>
          </div>
          <div className="mt-6 space-y-4">
            <label className="research-label">Execution context<select className="research-select mt-2" defaultValue="pending"><option value="pending">Awaiting backend capability</option><option value="simulator">Simulator</option><option value="hardware">Hardware</option></select></label>
            <label className="research-label">Noise assumption<select className="research-select mt-2" defaultValue="pending"><option value="pending">Declare with measured run</option><option value="depolarizing">Depolarizing model</option><option value="backend">Backend-derived model</option></select></label>
            <label className="research-label">Mitigation method<select className="research-select mt-2" defaultValue="pending"><option value="pending">No method selected</option><option value="zne">Zero-noise extrapolation</option><option value="measurement">Measurement mitigation</option></select></label>
            <label className="research-label">Shot count<input className="research-input mt-2" inputMode="numeric" placeholder="Provided by backend run" /></label>
          </div>
          <Button className="mt-6 w-full" disabled><ShieldCheck size={15} /> Backend experiment required</Button>
        </Panel>

        <Panel className="p-5" aria-labelledby="noise-chart-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="research-eyebrow">Comparison chart</p><h2 id="noise-chart-heading" className="mt-1 text-lg font-semibold text-[#28323C]">Demo estimation-error comparison</h2><p className="mt-1 text-xs text-[#718791]">Arbitrary units. Mitigation is not assumed to improve a result.</p></div>
            <StatusPill tone="demo">DEMO</StatusPill>
          </div>
          <div className="mt-5 h-[17rem]" role="img" aria-label="Demo ideal noisy and mitigated estimation error bar chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={demoNoiseComparison} margin={{ top: 8, right: 14, left: -8, bottom: 16 }}>
                <CartesianGrid stroke="#E5EEF0" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="state" tick={{ fill: '#5E747F', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#C9D9DE' }} interval={0} />
                <YAxis tick={{ fill: '#5E747F', fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: 'Demo estimation error (a.u.)', angle: -90, position: 'insideLeft', fill: '#6B818B', fontSize: 11, dx: -2 }} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} a.u.`, 'Demo error']} contentStyle={{ border: '1px solid #D9E0E7', borderRadius: 8, boxShadow: '0 4px 16px rgba(23,43,58,0.08)' }} />
                <Bar dataKey="error" name="Demo estimation error" radius={[4, 4, 0, 0]} maxBarSize={72}>{demoNoiseComparison.map((entry, index) => <Cell key={entry.state} fill={barColors[index]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Panel className="p-4"><BarChart3 size={18} className="text-blue-700" /><h3 className="mt-3 text-sm font-semibold text-[#394957]">Record the baseline</h3><p className="mt-1 text-xs leading-5 text-[#718791]">Keep the unmitigated estimate, settings, and sampling context visible beside any mitigation output.</p></Panel>
        <Panel className="p-4"><AlertTriangle size={18} className="text-amber-700" /><h3 className="mt-3 text-sm font-semibold text-[#394957]">Report overhead</h3><p className="mt-1 text-xs leading-5 text-[#718791]">Shot count, circuit expansion, seed, noise assumptions, and uncertainty are essential to interpretation.</p></Panel>
        <Panel className="p-4"><ShieldCheck size={18} className="text-blue-700" /><h3 className="mt-3 text-sm font-semibold text-[#394957]">Avoid a guarantee</h3><p className="mt-1 text-xs leading-5 text-[#718791]">Mitigation may worsen an estimate; observed results should be reported rather than implied.</p></Panel>
      </section>

      <p className="text-xs text-[#718791]">Provenance: {demoProvenance.label}. This optional lab remains separate from core peptide-blend scoring and selection.</p>
    </div>
  )
}
