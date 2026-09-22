'use client'

import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { PriceBar } from '@/lib/types'

interface PriceChartProps {
  bars: PriceBar[]
}

const COLOR_PRICE = '#ffffff'
const COLOR_SMA20 = '#3987e5'
const COLOR_SMA50 = '#d95926'
const COLOR_SMA200 = '#e34948'
const COLOR_BAND = '#898781'
const COLOR_GRID = '#2c2c2a'
const COLOR_MUTED = '#898781'

function formatTick(value: string) {
  const d = new Date(value)
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

export default function PriceChart({ bars }: PriceChartProps) {
  const tickInterval = Math.max(Math.floor(bars.length / 6), 1)

  return (
    <div className="chart-card card">
      <h3>Price &amp; Moving Averages</h3>
      <div className="chart-legend">
        <span>
          <span className="swatch" style={{ background: COLOR_PRICE }} />
          Close
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_SMA20 }} />
          SMA 20
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_SMA50 }} />
          SMA 50
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_SMA200 }} />
          SMA 200
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_MUTED }} />
          Bollinger Bands
        </span>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={bars} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
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
            domain={['auto', 'auto']}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
            width={56}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                close: 'Close', sma_20: 'SMA 20', sma_50: 'SMA 50', sma_200: 'SMA 200',
                bb_upper: 'BB Upper', bb_lower: 'BB Lower',
              }
              return [value != null ? `$${value.toFixed(2)}` : '—', labels[name] ?? name]
            }}
          />
          <Line
            type="monotone" dataKey="bb_upper" stroke={COLOR_BAND} strokeWidth={1}
            strokeDasharray="3 3" dot={false} connectNulls
          />
          <Line
            type="monotone" dataKey="bb_lower" stroke={COLOR_BAND} strokeWidth={1}
            strokeDasharray="3 3" dot={false} connectNulls
          />
          <Line type="monotone" dataKey="close" stroke={COLOR_PRICE} strokeWidth={2} dot={false} connectNulls />
          <Line type="monotone" dataKey="sma_20" stroke={COLOR_SMA20} strokeWidth={1.5} dot={false} connectNulls />
          <Line type="monotone" dataKey="sma_50" stroke={COLOR_SMA50} strokeWidth={1.5} dot={false} connectNulls />
          <Line type="monotone" dataKey="sma_200" stroke={COLOR_SMA200} strokeWidth={1.5} dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
