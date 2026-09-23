'use client'

import { Fragment, useEffect, useState } from 'react'
import { ApiError, fetchDashboard } from '@/lib/api'
import type { DashboardRow } from '@/lib/types'
import SignalPill from './SignalPill'

function fmtMoney(v: number | undefined): string {
  if (v == null) return '—'
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// Actionable rows (a fresh buy/sell somewhere) float to the top — a hold
// just means "nothing new today," which is most rows most days.
function sortRows(rows: DashboardRow[]): DashboardRow[] {
  const rank = (r: DashboardRow) => (r.error ? 2 : r.consensus === 'hold' || !r.consensus ? 1 : 0)
  return [...rows].map((r, i) => ({ r, i })).sort((a, b) => rank(a.r) - rank(b.r) || a.i - b.i).map((x) => x.r)
}

export default function DashboardView() {
  const [rows, setRows] = useState<DashboardRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDashboard()
      setRows(sortRows(data.rows))
      setLastUpdated(new Date())
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't reach the dashboard API.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const buyCount = rows.filter((r) => r.consensus === 'buy').length
  const sellCount = rows.filter((r) => r.consensus === 'sell').length

  return (
    <div className="results">
      <div className="card">
        <div className="rec-row-top" style={{ marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>🌍 Dashboard</h2>
          <button type="button" className="chip" onClick={load} disabled={loading}>
            {loading ? <span className="spinner" /> : '↻'} Refresh
          </button>
        </div>
        <p className="meta" style={{ marginBottom: 8 }}>
          One consensus call per asset — a majority vote across all 5 strategies&apos; current
          signal. Assets with an active BUY or SELL are sorted to the top; a HOLD just means
          nothing changed today for that asset. Click a row for the per-strategy breakdown.
        </p>
        <div className="inline-controls" style={{ marginBottom: 0 }}>
          {buyCount > 0 && <span className="pill win">⬆ {buyCount} BUY</span>}
          {sellCount > 0 && <span className="pill loss">⬇ {sellCount} SELL</span>}
          {buyCount === 0 && sellCount === 0 && !loading && (
            <span className="pill open">Nothing actionable right now</span>
          )}
          {lastUpdated && (
            <span className="meta" style={{ marginLeft: 'auto' }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        {error && <div className="error-banner" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      <div className="table-card card">
        {rows.length === 0 && !loading ? (
          <div className="empty-state" style={{ padding: '24px 12px' }}>
            No data yet — click Refresh.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Close</th>
                  <th>Consensus</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <Fragment key={r.ticker}>
                    <tr
                      className={expanded === r.ticker ? 'open-row' : undefined}
                      onClick={() => !r.error && setExpanded(expanded === r.ticker ? null : r.ticker)}
                      style={{ cursor: r.error ? 'default' : 'pointer' }}
                    >
                      <td>{r.ticker}</td>
                      <td>{r.error ? '—' : fmtMoney(r.close)}</td>
                      <td>
                        {r.error ? (
                          <span className="pill loss" title={r.error}>
                            Error
                          </span>
                        ) : (
                          <SignalPill signal={r.consensus ?? 'hold'} />
                        )}
                      </td>
                    </tr>
                    {expanded === r.ticker && r.recommendations && (
                      <tr>
                        <td colSpan={3} style={{ padding: 0 }}>
                          <div className="rec-grid" style={{ padding: '12px' }}>
                            {r.recommendations.map((rec) => (
                              <div key={rec.strategy_id} className="rec-row">
                                <div className="rec-row-top">
                                  <span className="rec-name">{rec.strategy_name}</span>
                                  <SignalPill signal={rec.signal} />
                                </div>
                                {rec.reason && <p className="rec-reason">{rec.reason}</p>}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
