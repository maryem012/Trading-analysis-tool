'use client'

import { useEffect, useState } from 'react'
import { ApiError, fetchAccount, fetchBrokerStatus, fetchOrders, fetchPositions } from '@/lib/api'
import type { Account, BrokerOrder, Position, StrategyOption } from '@/lib/types'

interface PortfolioViewProps {
  assets: string[]
  strategies: StrategyOption[]
}

function fmtMoney(v: number | null): string {
  if (v == null) return '—'
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPct(v: number | null): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

export default function PortfolioView({ assets: _assets, strategies: _strategies }: PortfolioViewProps) {
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [account, setAccount] = useState<Account | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<BrokerOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const status = await fetchBrokerStatus()
      setConfigured(status.configured)
      if (status.configured) {
        const [a, p, o] = await Promise.all([fetchAccount(), fetchPositions(), fetchOrders(20)])
        setAccount(a)
        setPositions(p)
        setOrders(o)
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't reach the broker API.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="results">
      <div className="card">
        <div className="rec-row-top" style={{ marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>💼 Portfolio</h2>
          <button type="button" className="chip" onClick={load} disabled={loading}>
            {loading ? <span className="spinner" /> : '↻'} Refresh
          </button>
        </div>
        <p className="meta" style={{ marginBottom: 12 }}>
          A real Alpaca paper-trading account — fake money, real order mechanics and market
          data. Nothing here risks actual funds.
        </p>

        {configured !== null && (
          <span className={configured ? 'live-dot on' : 'live-dot'} style={{ marginRight: 8 }} />
        )}
        {configured === true && <span className="pill win">Broker connected (paper)</span>}
        {configured === false && <span className="pill loss">Broker not connected</span>}

        {error && <div className="error-banner" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      {configured === false && (
        <div className="card">
          <div className="empty-state">
            No Alpaca API keys are set on the backend yet. Set <code>ALPACA_API_KEY</code> and{' '}
            <code>ALPACA_SECRET_KEY</code> (a free paper-trading key pair from alpaca.markets) in
            the backend&apos;s environment, then refresh this page.
          </div>
        </div>
      )}

      {configured === true && account && (
        <div className="card">
          <h3>Account</h3>
          <div className="metric-grid">
            <div className="metric-card">
              <div className="label">Portfolio Value</div>
              <div className="value">{fmtMoney(account.portfolio_value)}</div>
            </div>
            <div className="metric-card">
              <div className="label">Cash</div>
              <div className="value">{fmtMoney(account.cash)}</div>
            </div>
            <div className="metric-card">
              <div className="label">Buying Power</div>
              <div className="value">{fmtMoney(account.buying_power)}</div>
              <div className="sub">includes margin — not all spendable cash</div>
            </div>
            <div className="metric-card">
              <div className="label">Account Status</div>
              <div className="value">{account.status}</div>
            </div>
          </div>
        </div>
      )}

      {configured === true && (
        <div className="table-card card">
          <h3>Positions</h3>
          {positions.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 12px' }}>
              No open positions yet.
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Qty</th>
                    <th>Avg Entry</th>
                    <th>Current</th>
                    <th>Market Value</th>
                    <th>Unrealized P&amp;L</th>
                    <th>Unrealized %</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.ticker}>
                      <td>{p.ticker}</td>
                      <td>{p.qty}</td>
                      <td>{fmtMoney(p.avg_entry_price)}</td>
                      <td>{fmtMoney(p.current_price)}</td>
                      <td>{fmtMoney(p.market_value)}</td>
                      <td className={p.unrealized_pl >= 0 ? 'text-good' : 'text-bad'}>
                        {fmtMoney(p.unrealized_pl)}
                      </td>
                      <td className={p.unrealized_plpc >= 0 ? 'text-good' : 'text-bad'}>
                        {fmtPct(p.unrealized_plpc)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {configured === true && (
        <div className="table-card card">
          <h3>Order History</h3>
          {orders.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 12px' }}>
              No orders placed yet.
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Submitted</th>
                    <th>Ticker</th>
                    <th>Side</th>
                    <th>Qty / Notional</th>
                    <th>Fill Price</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id}>
                      <td>{o.submitted_at ? new Date(o.submitted_at).toLocaleString() : '—'}</td>
                      <td>{o.ticker}</td>
                      <td>{o.side ?? '—'}</td>
                      <td>{o.qty != null ? o.qty : fmtMoney(o.notional)}</td>
                      <td>{fmtMoney(o.filled_avg_price)}</td>
                      <td>{o.status ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
