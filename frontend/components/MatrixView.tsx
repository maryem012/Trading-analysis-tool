'use client'

import { useState } from 'react'
import { ApiError, runMatrix } from '@/lib/api'
import type { MatrixResponse } from '@/lib/types'
import HeatmapGrid from './HeatmapGrid'
import StrategyTable from './StrategyTable'

const MAX_TICKERS = 8
const DEFAULT_TICKERS = 'SPY, URTH, ^GSPC'

interface MatrixViewProps {
  assets: string[]
}

function parseTickers(raw: string): string[] {
  const seen = new Set<string>()
  for (const part of raw.split(',')) {
    const t = part.trim().toUpperCase()
    if (t) seen.add(t)
  }
  return Array.from(seen)
}

export default function MatrixView({ assets }: MatrixViewProps) {
  const [tickersInput, setTickersInput] = useState(DEFAULT_TICKERS)
  const [years, setYears] = useState(2)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<MatrixResponse | null>(null)

  const tickers = parseTickers(tickersInput)

  function addTicker(t: string) {
    if (tickers.includes(t) || tickers.length >= MAX_TICKERS) return
    setTickersInput([...tickers, t].join(', '))
  }

  async function run() {
    if (tickers.length === 0) {
      setError('Enter at least one ticker.')
      return
    }
    if (tickers.length > MAX_TICKERS) {
      setError(`Up to ${MAX_TICKERS} tickers per run — you have ${tickers.length}.`)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await runMatrix({ years, tickers })
      setResult(data)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to run the asset matrix.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="results">
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault()
          run()
        }}
      >
        <div className="inline-controls">
          <div className="field" style={{ flex: '1 1 320px' }}>
            <label htmlFor="matrix-tickers">
              Tickers ({tickers.length}/{MAX_TICKERS})
            </label>
            <input
              id="matrix-tickers"
              type="text"
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              placeholder="AAPL, MSFT, BTC-USD, SPY..."
              spellCheck={false}
              autoComplete="off"
            />
          </div>
          <div className="field">
            <label htmlFor="matrix-years">History (years)</label>
            <select id="matrix-years" value={years} onChange={(e) => setYears(Number(e.target.value))}>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={5}>5</option>
            </select>
          </div>
          <button type="submit" className="run-button inline" disabled={loading}>
            {loading ? <span className="spinner" /> : '▶'} Run Full Matrix
          </button>
        </div>

        <div className="chip-row">
          <span className="meta">Quick add:</span>
          {assets
            .filter((a) => !tickers.includes(a))
            .slice(0, 12)
            .map((a) => (
              <button
                type="button"
                key={a}
                className="chip"
                onClick={() => addTicker(a)}
                disabled={tickers.length >= MAX_TICKERS}
              >
                + {a}
              </button>
            ))}
        </div>

        <p className="meta" style={{ marginTop: 8, marginBottom: 0 }}>
          Every strategy × every ticker above — {tickers.length || 0} tickers × 5 strategies ={' '}
          {(tickers.length || 0) * 5} backtests. First run per ticker/window can take a few
          seconds (uncached data).
        </p>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <>
          <HeatmapGrid
            rows={result.rows}
            metric="total_return_pct"
            label="Total Return (%)"
            title="Total Return — Strategy × Asset"
          />
          <HeatmapGrid
            rows={result.rows}
            metric="sharpe_ratio"
            label="Sharpe Ratio"
            title="Sharpe Ratio — Strategy × Asset"
          />
          <StrategyTable rows={result.rows} title="Full Matrix" showTicker />
        </>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">
          Run every strategy against every asset to see what actually works, and where.
        </div>
      )}
    </div>
  )
}
