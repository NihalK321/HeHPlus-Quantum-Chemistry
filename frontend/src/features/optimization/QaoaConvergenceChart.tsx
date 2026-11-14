import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { demoConvergence } from '../../demo/researchDemo'

export function QaoaConvergenceChart() {
  return (
    <div className="h-[17rem] w-full" role="img" aria-label="Demo QAOA convergence plot showing an illustrative objective trajectory over six iterations">
      <ResponsiveContainer height="100%" width="100%">
        <LineChart data={demoConvergence} margin={{ top: 12, right: 18, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#E4EEF0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            axisLine={{ stroke: '#C9D9DE' }}
            dataKey="iteration"
            label={{ value: 'Iteration', position: 'insideBottom', offset: -3, fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            domain={[0.55, 1.05]}
            label={{ value: 'Demo objective (a.u.)', angle: -90, position: 'insideLeft', fill: '#607680', fontSize: 11 }}
            tick={{ fill: '#607680', fontSize: 11 }}
            tickLine={false}
            width={54}
          />
          <Tooltip
            contentStyle={{ border: '1px solid #D9E0E7', borderRadius: 8, boxShadow: '0 8px 18px rgba(23,43,58,.08)', fontSize: 12 }}
            cursor={{ stroke: '#9CBEC0', strokeDasharray: '3 3' }}
            formatter={(value) => [`${Number(value).toFixed(2)} a.u.`, 'Demo objective']}
            labelFormatter={(label) => `Iteration ${label}`}
          />
          <Line activeDot={{ r: 4 }} dataKey="objective" dot={{ r: 3, fill: '#087E78', strokeWidth: 0 }} name="Demo objective" stroke="#087E78" strokeWidth={2.25} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
