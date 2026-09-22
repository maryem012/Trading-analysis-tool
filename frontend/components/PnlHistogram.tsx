'use client'

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Trade } from '@/lib/types'

interface PnlHistogramProps {
  trades: Trade[]
}

const COLOR_GOOD = '#0ca30c'
const COLOR_BAD = '#d03b3b'
const COLOR_GRID = '#2c2c2a'
const COLOR_MUTED = '#898781'

const BIN_COUNT = 8

export default function PnlHistogram({ trades }: PnlHistogramProps) {
  const values = trades
    .filter((t) => t.status === 'closed' && t.profit_loss != null)
    .map((t) => t.profit_loss as number)

  if (values.length < 2) {
    return (
      <div className="chart-card card">
        <h3>Trade P&amp;L Distribution</h3>
        <div className="empty-state" style={{ padding: '24px 12px' }}>
          Not enough closed trades yet ({values.length}) to plot a distribution.
        </div>
      </div>
    )
  }

  const min = Math.min(...values, 0)
  const max = Math.max(...values, 0)
  const span = max - min || 1
  const binWidth = span / BIN_COUNT

  const bins = Array.from({ length: BIN_COUNT }, (_, i) => {
    const lo = min + i * binWidth
    const hi = lo + binWidth
    return { lo, hi, count: 0 }
  })
  for (const v of values) {
    let idx = Math.floor((v - min) / binWidth)
    if (idx >= BIN_COUNT) idx = BIN_COUNT - 1
    if (idx < 0) idx = 0
    bins[idx].count += 1
  }

  const data = bins.map((b) => ({
    label: `$${b.lo.toFixed(0)}`,
    count: b.count,
    midpoint: (b.lo + b.hi) / 2,
  }))

  return (
    <div className="chart-card card">
      <h3>Trade P&amp;L Distribution</h3>
      <div className="chart-legend">
        <span>
          <span className="swatch" style={{ background: COLOR_GOOD }} />
          Winning bins
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_BAD }} />
          Losing bins
        </span>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={COLOR_GRID} vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: COLOR_MUTED, fontSize: 10 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
            width={32}
          />
          <ReferenceLine x={0} stroke={COLOR_MUTED} />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
            formatter={(value: number) => [`${value} trade${value === 1 ? '' : 's'}`, 'Count']}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.midpoint >= 0 ? COLOR_GOOD : COLOR_BAD} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
