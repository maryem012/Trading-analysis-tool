'use client'

import { useEffect, useRef, useState } from 'react'
import { ApiError, fetchPriceHistory, fetchSignals } from '@/lib/api'
import type { PriceHistoryResponse, SignalsResponse } from '@/lib/types'
import SignalBanner from './SignalBanner'
import PriceChart from './PriceChart'
import VolumeChart from './VolumeChart'
import MomentumChart from './MomentumChart'
import TickerInput from './TickerInput'

interface MarketViewProps {
  assets: string[]
}

const REFRESH_OPTIONS = [
  { value: 30, label: '30s' },
  { value: 60, label: '1 min' },
  { value: 300, label: '5 min' },
]

export default function MarketView({ assets }: MarketViewProps) {
  const [ticker, setTicker] = useState('SPY')
  const [days, setDays] = useState(365)
  // The ticker/days actually loaded, decoupled from the input field — so
  // auto-refresh keeps reloading what's on screen, not whatever's half-typed
  const [activeTicker, setActiveTicker] = useState('SPY')
  const [activeDays, setActiveDays] = useState(365)

  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshSec, setRefreshSec] = useState(60)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [signals, setSignals] = useState<SignalsResponse | null>(null)
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null)

  const loadingRef = useRef(loading)
  loadingRef.current = loading

  async function load(t: string, d: number) {
    setActiveTicker(t)
    setActiveDays(d)
    setLoading(true)
    setError(null)
    try {
      const [s, h] = await Promise.all([fetchSignals(t), fetchPriceHistory(t, d)])
      setSignals(s)
      setHistory(h)
      setLastUpdated(new Date())
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load market data.')
      setSignals(null)
      setHistory(null)
    } finally {
      setLoading(false)
    }
  }

  // Initial load once the strategy/asset lists are ready
  useEffect(() => {
    if (assets.length) load(ticker, days)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assets])

  // Auto-refresh: reload whatever's currently on screen on a timer. Skips a
  // tick if a fetch is already in flight instead of piling requests up.
  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(() => {
      if (!loadingRef.current) load(activeTicker, activeDays)
    }, refreshSec * 1000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, refreshSec, activeTicker, activeDays])

  return (
    <div className="results">
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault()
          load(ticker, days)
        }}
      >
        <div className="inline-controls">
          <div className="field">
            <label htmlFor="market-ticker">Ticker</label>
            <TickerInput id="market-ticker" value={ticker} onChange={setTicker} suggestions={assets} />
          </div>
          <div className="field">
            <label htmlFor="market-days">History (days)</label>
            <select id="market-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={90}>90</option>
              <option value={180}>180</option>
              <option value={365}>365</option>
              <option value={730}>730</option>
              <option value={1825}>1825 (5y)</option>
              <option value={3650}>3650 (10y)</option>
            </select>
          </div>
          <button type="submit" className="run-button inline" disabled={loading}>
            {loading ? <span className="spinner" /> : '↻'} Load
          </button>
        </div>

        <div className="refresh-row">
          <label className="refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span className={autoRefresh ? 'live-dot on' : 'live-dot'} />
            Auto-refresh every
          </label>
          <select
            value={refreshSec}
            onChange={(e) => setRefreshSec(Number(e.target.value))}
            disabled={!autoRefresh}
          >
            {REFRESH_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <span className="meta">
            {lastUpdated
              ? `Updated ${lastUpdated.toLocaleTimeString('en-US')}`
              : 'Not loaded yet'}
          </span>
        </div>
        <p className="meta refresh-note">
          Prices update once per trading day, not tick-by-tick — auto-refresh means you&apos;ll
          see a new day&apos;s close the moment it posts, without clicking Load yourself.
        </p>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {signals && <SignalBanner data={signals} />}

      {history && history.bars.length > 0 && (
        <>
          <PriceChart bars={history.bars} />
          <VolumeChart bars={history.bars} />
          <MomentumChart bars={history.bars} />
        </>
      )}

      {!signals && !history && !loading && !error && (
        <div className="empty-state">Pick a ticker above and hit Load.</div>
      )}
    </div>
  )
}
