'use client'

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { PriceBar } from '@/lib/types'

interface VolumeChartProps {
  bars: PriceBar[]
}

const COLOR_UP = '#0ca30c'
const COLOR_DOWN = '#d03b3b'
const COLOR_GRID = '#2c2c2a'
const COLOR_MUTED = '#898781'

function formatTick(value: string) {
  const d = new Date(value)
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

export default function VolumeChart({ bars }: VolumeChartProps) {
  const tickInterval = Math.max(Math.floor(bars.length / 6), 1)
  const data = bars.map((b, i) => ({
    date: b.date,
    volume: b.volume,
    up: i === 0 || b.close >= bars[i - 1].close,
  }))

  return (
    <div className="chart-card card">
      <h3>Volume</h3>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={COLOR_GRID} vertical={false} />
          <XAxis
            dataKey="date"
            interval={tickInterval}
            tickFormatter={formatTick}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
            width={56}
            tickFormatter={(v: number) => `${(v / 1_000_000).toFixed(0)}M`}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
            formatter={(value: number) => [value.toLocaleString('en-US'), 'Volume']}
          />
          <Bar dataKey="volume" isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.up ? COLOR_UP : COLOR_DOWN} fillOpacity={0.55} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
