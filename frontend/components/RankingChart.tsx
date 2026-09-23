'use client'

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { StrategyRow } from '@/lib/types'

interface RankingChartProps {
  rows: StrategyRow[]
  metric: keyof StrategyRow
  label: string
  title: string
}

const COLOR_GOOD = '#0ca30c'
const COLOR_BAD = '#d03b3b'
const COLOR_GRID = '#2c2c2a'
const COLOR_MUTED = '#898781'

export default function RankingChart({ rows, metric, label, title }: RankingChartProps) {
  const data = rows
    .filter((r) => r[metric] != null)
    .map((r) => ({ name: r.strategy, value: Number(r[metric]) }))
    .filter((d) => Number.isFinite(d.value))
    .sort((a, b) => a.value - b.value)

  return (
    <div className="chart-card card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={60 + 48 * data.length}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
          <CartesianGrid stroke={COLOR_GRID} horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={150}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
          />
          <ReferenceLine x={0} stroke={COLOR_MUTED} />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
            formatter={(v: number) => [v.toFixed(2), label]}
          />
          <Bar dataKey="value" radius={[0, 3, 3, 0]} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.value >= 0 ? COLOR_GOOD : COLOR_BAD} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
