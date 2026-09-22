'use client'

import { useState } from 'react'
import ControlPanel from './ControlPanel'
import MetricCard from './MetricCard'
import Verdict from './Verdict'
import EquityChart from './EquityChart'
import PnlHistogram from './PnlHistogram'
import TradeTable from './TradeTable'
import { ApiError, runBacktest } from '@/lib/api'
import type { BacktestResponse, StrategyOption } from '@/lib/types'

interface BacktestViewProps {
  assets: string[]
  strategies: StrategyOption[]
}

export default function BacktestView({ assets, strategies }: BacktestViewProps) {
  const [ticker, setTicker] = useState('SPY')
  const [strategy, setStrategy] = useState('sma_crossover')
  const [days, setDays] = useState(365)
  const [initialCapital, setInitialCapital] = useState(10_000)
  const [riskPerTrade, setRiskPerTrade] = useState(2)
  const [stopLossPct, setStopLossPct] = useState(5)
  const [takeProfitPct, setTakeProfitPct] = useState(10)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BacktestResponse | null>(null)

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      const data = await runBacktest({
        ticker, strategy, days,
        initial_capital: initialCapital,
        risk_per_trade: riskPerTrade,
        stop_loss_pct: stopLossPct,
        take_profit_pct: takeProfitPct,
      })
      setResult(data)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong running the backtest.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const m = result?.metrics

  return (
    <div className="layout">
      <ControlPanel
        assets={assets}
        strategies={strategies}
        ticker={ticker}
        onTickerChange={setTicker}
        strategy={strategy}
        onStrategyChange={setStrategy}
        days={days}
        onDaysChange={setDays}
        initialCapital={initialCapital}
        onInitialCapitalChange={setInitialCapital}
        riskPerTrade={riskPerTrade}
        onRiskPerTradeChange={setRiskPerTrade}
        stopLossPct={stopLossPct}
        onStopLossPctChange={setStopLossPct}
        takeProfitPct={takeProfitPct}
        onTakeProfitPctChange={setTakeProfitPct}
        onRun={handleRun}
        loading={loading}
      />

      <div className="results">
        {error && <div className="error-banner">{error}</div>}

        {!result && !error && (
          <div className="empty-state">
            Configure a backtest on the left, then hit <strong>Run Backtest</strong>.
          </div>
        )}

        {result && m && (
          <>
            <p className="result-context">
              Simulating <strong>${result.initial_capital.toLocaleString('en-US')} of fake money</strong>{' '}
              trading <strong>{result.ticker}</strong> with the <strong>{result.strategy}</strong>{' '}
              rule, over the last {result.days} days ({m.bars} trading days of real price history).
            </p>

            <div className="metric-grid">
              <MetricCard
                label="Total Return"
                value={`${m.total_return_pct >= 0 ? '+' : ''}${m.total_return_pct.toFixed(2)}%`}
                tone={m.total_return_pct >= 0 ? 'good' : 'bad'}
                sub={`vs. buy & hold ${m.buy_hold_return_pct >= 0 ? '+' : ''}${m.buy_hold_return_pct.toFixed(2)}%`}
                hint="How much your starting amount grew or shrank. Compare it to 'buy & hold' — just buying once and doing nothing — since that's the real bar to beat."
              />
              <MetricCard
                label="Win Rate"
                value={`${m.win_rate_pct.toFixed(1)}%`}
                sub={`${m.winning_trades}W / ${m.losing_trades}L (${m.closed_trades} closed)`}
                hint="Percent of trades that made money. Only meaningful with dozens of trades — a great win rate on 3 trades is luck, not a pattern."
              />
              <MetricCard
                label="Sharpe Ratio"
                value={m.sharpe_ratio.toFixed(2)}
                tone={m.sharpe_ratio >= 0 ? 'good' : 'bad'}
                sub="annualized"
                hint="Return per unit of bumpiness. Rough guide: above 1 is decent, above 2 is strong, below 0 means it lost money."
              />
              <MetricCard
                label="Max Drawdown"
                value={`${m.max_drawdown_pct.toFixed(2)}%`}
                tone="bad"
                sub={`${m.avg_trade_duration_days.toFixed(0)}d avg hold`}
                hint="The worst drop from a peak. A -30% drawdown means the account lost almost a third of its value at some point before recovering."
              />
            </div>

            <Verdict
              metrics={m}
              ticker={result.ticker}
              strategyName={result.strategy}
              initialCapital={result.initial_capital}
            />

            <div className="chart-grid">
              <EquityChart equityCurve={result.equity_curve} buyHoldCurve={result.buy_hold_curve} />
              <PnlHistogram trades={result.trades} />
            </div>

            <TradeTable trades={result.trades} />
          </>
        )}
      </div>
    </div>
  )
}
