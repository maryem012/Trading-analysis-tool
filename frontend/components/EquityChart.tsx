'use client'

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { EquityPoint } from '@/lib/types'

interface EquityChartProps {
  equityCurve: EquityPoint[]
  buyHoldCurve: EquityPoint[]
}

const COLOR_EQUITY = '#3987e5'
const COLOR_BENCH = '#d95926'
const COLOR_GRID = '#2c2c2a'
const COLOR_MUTED = '#898781'

export default function EquityChart({ equityCurve, buyHoldCurve }: EquityChartProps) {
  const byDate = new Map<string, { date: string; strategy: number | null; buyHold: number | null }>()
  for (const p of equityCurve) {
    byDate.set(p.date, { date: p.date, strategy: p.equity, buyHold: null })
  }
  for (const p of buyHoldCurve) {
    const existing = byDate.get(p.date)
    if (existing) existing.buyHold = p.equity
    else byDate.set(p.date, { date: p.date, strategy: null, buyHold: p.equity })
  }
  const data = Array.from(byDate.values())

  // Thin the x-axis ticks so labels don't collide on a year+ of daily bars,
  // and show "Mon 'YY" instead of the full ISO date — plenty for an axis label
  const tickInterval = Math.max(Math.floor(data.length / 6), 1)
  const formatTick = (value: string) => {
    const d = new Date(value)
    return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
  }

  return (
    <div className="chart-card card">
      <h3>Equity Curve</h3>
      <div className="chart-legend">
        <span>
          <span className="swatch" style={{ background: COLOR_EQUITY }} />
          Strategy
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_BENCH }} />
          Buy &amp; Hold
        </span>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={COLOR_GRID} vertical={false} />
          <XAxis
            dataKey="date"
            interval={tickInterval}
            tickFormatter={formatTick}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
            width={64}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
            formatter={(value: number, name: string) => [
              value != null ? `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—',
              name === 'strategy' ? 'Strategy' : 'Buy & Hold',
            ]}
          />
          <Line
            type="monotone"
            dataKey="strategy"
            stroke={COLOR_EQUITY}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="buyHold"
            stroke={COLOR_BENCH}
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
