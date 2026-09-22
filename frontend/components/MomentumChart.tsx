'use client'

import {
  Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { PriceBar } from '@/lib/types'

interface MomentumChartProps {
  bars: PriceBar[]
}

const COLOR_RSI = '#9085e9'
const COLOR_MACD = '#3987e5'
const COLOR_SIGNAL = '#d95926'
const COLOR_GOOD = '#0ca30c'
const COLOR_BAD = '#d03b3b'
const COLOR_GRID = '#2c2c2a'
const COLOR_MUTED = '#898781'

function formatTick(value: string) {
  const d = new Date(value)
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

export default function MomentumChart({ bars }: MomentumChartProps) {
  const tickInterval = Math.max(Math.floor(bars.length / 6), 1)
  const data = bars.map((b) => ({
    date: b.date,
    rsi: b.rsi,
    macd: b.macd,
    macd_signal: b.macd_signal,
    histogram: b.macd != null && b.macd_signal != null ? b.macd - b.macd_signal : null,
  }))

  return (
    <div className="chart-card card">
      <h3>RSI (14)</h3>
      <ResponsiveContainer width="100%" height={160}>
        <ComposedChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
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
            domain={[0, 100]}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
            width={32}
          />
          <ReferenceLine y={70} stroke={COLOR_BAD} strokeDasharray="4 3" />
          <ReferenceLine y={30} stroke={COLOR_GOOD} strokeDasharray="4 3" />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
            formatter={(v: number) => [v?.toFixed(1) ?? '—', 'RSI']}
          />
          <Line type="monotone" dataKey="rsi" stroke={COLOR_RSI} strokeWidth={2} dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>

      <h3 style={{ marginTop: 20 }}>MACD</h3>
      <div className="chart-legend">
        <span>
          <span className="swatch" style={{ background: COLOR_MACD }} />
          MACD
        </span>
        <span>
          <span className="swatch" style={{ background: COLOR_SIGNAL }} />
          Signal
        </span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <ComposedChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={COLOR_GRID} vertical={false} />
          <XAxis
            dataKey="date"
            interval={tickInterval}
            tickFormatter={formatTick}
            tick={{ fill: COLOR_MUTED, fontSize: 11 }}
            axisLine={{ stroke: COLOR_GRID }}
            tickLine={false}
          />
          <YAxis tick={{ fill: COLOR_MUTED, fontSize: 11 }} axisLine={{ stroke: COLOR_GRID }} tickLine={false} width={40} />
          <ReferenceLine y={0} stroke={COLOR_MUTED} />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 8 }}
            labelStyle={{ color: '#c3c2b7' }}
          />
          <Bar dataKey="histogram" fill={COLOR_MUTED} fillOpacity={0.4} isAnimationActive={false} />
          <Line type="monotone" dataKey="macd" stroke={COLOR_MACD} strokeWidth={2} dot={false} connectNulls />
          <Line type="monotone" dataKey="macd_signal" stroke={COLOR_SIGNAL} strokeWidth={2} dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
