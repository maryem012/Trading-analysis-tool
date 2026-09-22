'use client'

import { useState } from 'react'
import { ApiError, runCompare } from '@/lib/api'
import type { CompareResponse } from '@/lib/types'
import RankingChart from './RankingChart'
import StrategyTable from './StrategyTable'
import TickerInput from './TickerInput'

interface CompareViewProps {
  assets: string[]
}

export default function CompareView({ assets }: CompareViewProps) {
  const [ticker, setTicker] = useState('SPY')
  const [days, setDays] = useState(365)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CompareResponse | null>(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const data = await runCompare({ ticker, days })
      setResult(data)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to compare strategies.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="results">
      <form
        className="card inline-controls"
        onSubmit={(e) => {
          e.preventDefault()
          run()
        }}
      >
        <div className="field">
          <label htmlFor="compare-ticker">Ticker</label>
          <TickerInput id="compare-ticker" value={ticker} onChange={setTicker} suggestions={assets} />
        </div>
        <div className="field">
          <label htmlFor="compare-days">History (days)</label>
          <select id="compare-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={180}>180</option>
            <option value={365}>365</option>
            <option value={730}>730</option>
            <option value={1825}>1825 (5y)</option>
            <option value={3650}>3650 (10y)</option>
          </select>
        </div>
        <button type="submit" className="run-button inline" disabled={loading}>
          {loading ? <span className="spinner" /> : '▶'} Compare All Strategies
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <>
          <p className="meta">
            {result.ticker} · {result.start_date} → {result.end_date}
          </p>
          <RankingChart
            rows={result.rows}
            metric="total_return_pct"
            label="Total Return (%)"
            title="Total Return by Strategy"
          />
          <RankingChart
            rows={result.rows}
            metric="sharpe_ratio"
            label="Sharpe Ratio"
            title="Sharpe Ratio by Strategy"
          />
          <StrategyTable rows={result.rows} title="Strategy Comparison" />
        </>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">
          Pick a ticker and window, then run every strategy side by side.
        </div>
      )}
    </div>
  )
}
