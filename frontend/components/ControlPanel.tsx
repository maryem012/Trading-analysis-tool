'use client'

import type { StrategyOption } from '@/lib/types'
import TickerInput from './TickerInput'

interface ControlPanelProps {
  assets: string[]
  strategies: StrategyOption[]
  ticker: string
  onTickerChange: (v: string) => void
  strategy: string
  onStrategyChange: (v: string) => void
  days: number
  onDaysChange: (v: number) => void
  initialCapital: number
  onInitialCapitalChange: (v: number) => void
  riskPerTrade: number
  onRiskPerTradeChange: (v: number) => void
  stopLossPct: number
  onStopLossPctChange: (v: number) => void
  takeProfitPct: number
  onTakeProfitPctChange: (v: number) => void
  onRun: () => void
  loading: boolean
}

const CAPITAL_PRESETS = [100, 500, 1000, 10000]

export default function ControlPanel({
  assets,
  strategies,
  ticker,
  onTickerChange,
  strategy,
  onStrategyChange,
  days,
  onDaysChange,
  initialCapital,
  onInitialCapitalChange,
  riskPerTrade,
  onRiskPerTradeChange,
  stopLossPct,
  onStopLossPctChange,
  takeProfitPct,
  onTakeProfitPctChange,
  onRun,
  loading,
}: ControlPanelProps) {
  return (
    <form
      className="card control-panel"
      onSubmit={(e) => {
        e.preventDefault()
        onRun()
      }}
    >
      <h2>Backtest Settings</h2>

      <div className="field">
        <label htmlFor="ticker">Ticker</label>
        <TickerInput id="ticker" value={ticker} onChange={onTickerChange} suggestions={assets} />
      </div>

      <div className="field">
        <label htmlFor="strategy">Strategy</label>
        <select id="strategy" value={strategy} onChange={(e) => onStrategyChange(e.target.value)}>
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="capital">
          Starting Amount
          <span className="info-tip" title="Still fake money — set this to whatever you'd actually invest, so the results mean something to you.">
            ⓘ
          </span>
        </label>
        <div className="money-input">
          <span className="money-prefix">$</span>
          <input
            id="capital"
            type="number"
            min={10}
            max={1_000_000}
            step={10}
            value={initialCapital}
            onChange={(e) => onInitialCapitalChange(Math.max(10, Number(e.target.value) || 0))}
          />
        </div>
        <div className="chip-row" style={{ marginTop: 8 }}>
          {CAPITAL_PRESETS.map((p) => (
            <button
              type="button"
              key={p}
              className={`chip${initialCapital === p ? ' active' : ''}`}
              onClick={() => onInitialCapitalChange(p)}
            >
              ${p.toLocaleString('en-US')}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label htmlFor="days">History: {days} days (~{(days / 365).toFixed(1)}y)</label>
        <input
          id="days"
          type="range"
          min={30}
          max={3650}
          step={15}
          value={days}
          onChange={(e) => onDaysChange(Number(e.target.value))}
        />
        <div className="range-value">
          <span>30d</span>
          <span>3650d</span>
        </div>
      </div>

      <details className="advanced-settings">
        <summary>Advanced (risk &amp; exits)</summary>
        <div className="advanced-body">
          <div className="field">
            <label htmlFor="risk">Risk per trade: {riskPerTrade.toFixed(1)}%</label>
            <input
              id="risk"
              type="range"
              min={0.5}
              max={10}
              step={0.5}
              value={riskPerTrade}
              onChange={(e) => onRiskPerTradeChange(Number(e.target.value))}
            />
            <p className="field-note">How much of your starting amount to risk on one trade.</p>
          </div>
          <div className="field">
            <label htmlFor="stop">Stop-loss: {stopLossPct.toFixed(1)}%</label>
            <input
              id="stop"
              type="range"
              min={1}
              max={20}
              step={0.5}
              value={stopLossPct}
              onChange={(e) => onStopLossPctChange(Number(e.target.value))}
            />
            <p className="field-note">Exit automatically if the price drops this much from entry.</p>
          </div>
          <div className="field">
            <label htmlFor="target">Take-profit: {takeProfitPct.toFixed(1)}%</label>
            <input
              id="target"
              type="range"
              min={1}
              max={50}
              step={0.5}
              value={takeProfitPct}
              onChange={(e) => onTakeProfitPctChange(Number(e.target.value))}
            />
            <p className="field-note">Exit automatically once a gain like this is reached.</p>
          </div>
        </div>
      </details>

      <button type="submit" className="run-button" disabled={loading}>
        {loading ? (
          <>
            <span className="spinner" />
            Running...
          </>
        ) : (
          '▶ Run Backtest'
        )}
      </button>
    </form>
  )
}
