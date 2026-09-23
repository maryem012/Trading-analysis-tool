'use client'

import type { MatrixRow } from '@/lib/types'

interface HeatmapGridProps {
  rows: MatrixRow[]
  metric: 'total_return_pct' | 'sharpe_ratio'
  label: string
  title: string
}

// Same 5-stop diverging scale as the Python reports: cool = negative, warm =
// positive, neutral gray at the true zero — centered via the value's position
// between -max(|v|) and +max(|v|), not the raw data min/max.
const STOPS: [number, [number, number, number]][] = [
  [0.0, [13, 54, 107]], // #0d366b
  [0.25, [57, 135, 229]], // #3987e5
  [0.5, [240, 239, 236]], // #f0efec
  [0.75, [239, 133, 132]], // #ef8584
  [1.0, [227, 73, 72]], // #e34948
]

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function colorAt(t: number): string {
  t = Math.min(Math.max(t, 0), 1)
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [t0, c0] = STOPS[i]
    const [t1, c1] = STOPS[i + 1]
    if (t >= t0 && t <= t1) {
      const localT = (t - t0) / (t1 - t0)
      const r = Math.round(lerp(c0[0], c1[0], localT))
      const g = Math.round(lerp(c0[1], c1[1], localT))
      const b = Math.round(lerp(c0[2], c1[2], localT))
      return `rgb(${r},${g},${b})`
    }
  }
  return `rgb(${STOPS[STOPS.length - 1][1].join(',')})`
}

export default function HeatmapGrid({ rows, metric, label, title }: HeatmapGridProps) {
  const strategies = Array.from(new Set(rows.map((r) => r.strategy)))
  const tickers = Array.from(new Set(rows.map((r) => r.ticker)))
  const byKey = new Map(rows.map((r) => [`${r.strategy}|${r.ticker}`, r]))

  const values = rows.filter((r) => r[metric] != null).map((r) => Number(r[metric])).filter(Number.isFinite)
  const vmax = Math.max(...values.map(Math.abs), 1e-9)

  return (
    <div className="chart-card card">
      <h3>{title}</h3>
      <div className="heatmap-wrap">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th />
              {tickers.map((t) => (
                <th key={t}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {strategies.map((s) => (
              <tr key={s}>
                <th className="row-label">{s}</th>
                {tickers.map((t) => {
                  const row = byKey.get(`${s}|${t}`)
                  const v = row && row[metric] != null ? Number(row[metric]) : NaN
                  if (!Number.isFinite(v)) {
                    return (
                      <td key={t} className="heatmap-cell empty">
                        —
                      </td>
                    )
                  }
                  const norm = (v / vmax + 1) / 2 // -vmax..vmax -> 0..1
                  const bg = colorAt(norm)
                  const textColor = Math.abs(v) / vmax > 0.45 ? '#ffffff' : '#0b0b0b'
                  return (
                    <td
                      key={t}
                      className="heatmap-cell"
                      style={{ background: bg, color: textColor }}
                      title={`${s} on ${t}: ${v.toFixed(2)} ${label}${row?.has_edge ? ' (has edge)' : ''}`}
                    >
                      {v.toFixed(1)}
                      {row?.has_edge && <span className="edge-dot" title="Clears the edge bar" />}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="meta" style={{ marginTop: 8 }}>
        {label} — cool = worse, warm = better. A dot marks a cell that clears the edge bar
        (≥50 closed trades, ≥45% win rate, positive expectancy).
      </p>
    </div>
  )
}
