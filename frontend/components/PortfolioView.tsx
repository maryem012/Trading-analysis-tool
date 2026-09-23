'use client'

import { useEffect, useState } from 'react'
import {
  ApiError, closePosition, fetchAccount, fetchAutoTrade, fetchBrokerStatus, fetchOrders,
  fetchPositions, placeOrder, updateAutoTrade,
} from '@/lib/api'
import type { Account, AutoTradeItem, BrokerOrder, Position, StrategyOption } from '@/lib/types'
import TickerInput from './TickerInput'

interface PortfolioViewProps {
  assets: string[]
  strategies: StrategyOption[]
}

const MAX_AUTO_TRADE = 20

function fmtMoney(v: number | null): string {
  if (v == null) return '—'
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPct(v: number | null): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

export default function PortfolioView({ assets, strategies }: PortfolioViewProps) {
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [account, setAccount] = useState<Account | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<BrokerOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const nonCryptoAssets = assets.filter((a) => !a.toUpperCase().endsWith('-USD'))
  const [orderTicker, setOrderTicker] = useState('SPY')
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy')
  const [orderNotional, setOrderNotional] = useState(50)
  const [placing, setPlacing] = useState(false)
  const [orderError, setOrderError] = useState<string | null>(null)
  const [orderSuccess, setOrderSuccess] = useState<string | null>(null)
  const [closingTicker, setClosingTicker] = useState<string | null>(null)

  const [autoTrade, setAutoTrade] = useState<AutoTradeItem[]>([])
  const [autoTicker, setAutoTicker] = useState('SPY')
  const [autoStrategy, setAutoStrategy] = useState(strategies[0]?.id || 'sma_crossover')
  const [autoNotional, setAutoNotional] = useState(50)
  const [autoError, setAutoError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const status = await fetchBrokerStatus()
      setConfigured(status.configured)
      if (status.configured) {
        const [a, p, o, at] = await Promise.all([
          fetchAccount(), fetchPositions(), fetchOrders(20), fetchAutoTrade(),
        ])
        setAccount(a)
        setPositions(p)
        setOrders(o)
        setAutoTrade(at)
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

  useEffect(() => {
    if (strategies.length && !strategies.some((s) => s.id === autoStrategy)) {
      setAutoStrategy(strategies[0].id)
    }
  }, [strategies, autoStrategy])

  async function handlePlaceOrder() {
    setPlacing(true)
    setOrderError(null)
    setOrderSuccess(null)
    try {
      const o = await placeOrder({ ticker: orderTicker, side: orderSide, notional: orderNotional })
      setOrderSuccess(`${orderSide === 'buy' ? 'Bought' : 'Sold'} $${orderNotional} of ${o.ticker} — status: ${o.status}.`)
      await load()
    } catch (e) {
      setOrderError(e instanceof ApiError ? e.message : 'Order failed.')
    } finally {
      setPlacing(false)
    }
  }

  async function handleClosePosition(ticker: string) {
    setClosingTicker(ticker)
    setError(null)
    try {
      await closePosition(ticker)
      await load()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : `Couldn't close ${ticker}.`)
    } finally {
      setClosingTicker(null)
    }
  }

  async function syncAutoTrade(next: AutoTradeItem[]) {
    const prev = autoTrade
    setAutoTrade(next)
    setAutoError(null)
    try {
      await updateAutoTrade(next)
    } catch (e) {
      setAutoTrade(prev)
      setAutoError(e instanceof ApiError ? e.message : "Couldn't save auto-trade settings.")
    }
  }

  function addAutoTrade() {
    if (autoTrade.length >= MAX_AUTO_TRADE) return
    const exists = autoTrade.some((a) => a.ticker === autoTicker && a.strategy_id === autoStrategy)
    if (exists) return
    syncAutoTrade([...autoTrade, { ticker: autoTicker, strategy_id: autoStrategy, notional: autoNotional }])
  }

  function removeAutoTrade(i: number) {
    syncAutoTrade(autoTrade.filter((_, idx) => idx !== i))
  }

  const strategyName = (id: string) => strategies.find((s) => s.id === id)?.name || id

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
        <div className="card">
          <h3>Place an Order</h3>
          <p className="meta" style={{ marginBottom: 12 }}>
            Market orders by dollar amount, up to $1,000 per order. Crypto isn&apos;t supported
            here yet. Orders placed outside market hours (9:30–16:00 ET, weekdays) queue for the
            next open automatically.
          </p>
          <div className="inline-controls">
            <div className="field">
              <label htmlFor="order-ticker">Ticker</label>
              <TickerInput id="order-ticker" value={orderTicker} onChange={setOrderTicker} suggestions={nonCryptoAssets} />
            </div>
            <div className="field">
              <label htmlFor="order-side">Side</label>
              <select id="order-side" value={orderSide} onChange={(e) => setOrderSide(e.target.value as 'buy' | 'sell')}>
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="order-notional">Amount</label>
              <div className="money-input">
                <span className="money-prefix">$</span>
                <input
                  id="order-notional"
                  type="number"
                  min={1}
                  max={1000}
                  step={1}
                  value={orderNotional}
                  onChange={(e) => setOrderNotional(Number(e.target.value))}
                />
              </div>
            </div>
            <button type="button" className="run-button inline" onClick={handlePlaceOrder} disabled={placing}>
              {placing ? <span className="spinner" /> : '▶'} Place Order
            </button>
          </div>
          {orderError && <div className="error-banner" style={{ marginTop: 12 }}>{orderError}</div>}
          {orderSuccess && <p className="text-good" style={{ marginTop: 12 }}>{orderSuccess}</p>}
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
                    <th></th>
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
                      <td>
                        <button
                          type="button"
                          className="chip"
                          onClick={() => handleClosePosition(p.ticker)}
                          disabled={closingTicker === p.ticker}
                        >
                          {closingTicker === p.ticker ? <span className="spinner" /> : 'Close'}
                        </button>
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

      {configured === true && (
        <div className="card">
          <h3>Auto-Trade ({autoTrade.length}/{MAX_AUTO_TRADE})</h3>
          <p className="meta" style={{ marginBottom: 12 }}>
            The moment a watched strategy&apos;s signal flips to BUY or SELL, this places (or
            closes) a paper order automatically — checked on the same interval as Alerts. Off by
            default; nothing trades until you add a pair below.
          </p>

          <div className="inline-controls" style={{ marginBottom: 4 }}>
            <div className="field">
              <label htmlFor="auto-ticker">Ticker</label>
              <TickerInput id="auto-ticker" value={autoTicker} onChange={setAutoTicker} suggestions={nonCryptoAssets} />
            </div>
            <div className="field">
              <label htmlFor="auto-strategy">Strategy</label>
              <select id="auto-strategy" value={autoStrategy} onChange={(e) => setAutoStrategy(e.target.value)}>
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="auto-notional">Amount</label>
              <div className="money-input">
                <span className="money-prefix">$</span>
                <input
                  id="auto-notional"
                  type="number"
                  min={1}
                  max={1000}
                  step={1}
                  value={autoNotional}
                  onChange={(e) => setAutoNotional(Number(e.target.value))}
                />
              </div>
            </div>
            <button
              type="button"
              className="run-button inline"
              onClick={addAutoTrade}
              disabled={autoTrade.length >= MAX_AUTO_TRADE}
            >
              + Add
            </button>
          </div>

          {autoError && <div className="error-banner" style={{ marginTop: 8 }}>{autoError}</div>}

          {autoTrade.length === 0 ? (
            <div className="empty-state">Nothing set to auto-trade yet.</div>
          ) : (
            <ul className="watchlist">
              {autoTrade.map((a, i) => (
                <li key={`${a.ticker}-${a.strategy_id}`}>
                  <span>
                    <strong>{a.ticker}</strong> — {strategyName(a.strategy_id)} — ${a.notional}/trade
                  </span>
                  <button type="button" className="watchlist-remove" onClick={() => removeAutoTrade(i)}>
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
