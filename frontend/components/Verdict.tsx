'use client'

import type { Metrics } from '@/lib/types'

interface VerdictProps {
  metrics: Metrics
  ticker: string
  strategyName: string
  initialCapital: number
}

interface Check {
  ok: boolean
  label: string
  detail: string
}

export default function Verdict({ metrics: m, ticker, strategyName, initialCapital }: VerdictProps) {
  const beatsBuyHold = m.total_return_pct > m.buy_hold_return_pct
  const enoughTrades = m.closed_trades >= 50
  const positiveExpectancy = m.expectancy_pct > 0

  const checks: Check[] = [
    {
      ok: beatsBuyHold,
      label: 'Beats just buying and holding',
      detail: beatsBuyHold
        ? `+${m.total_return_pct.toFixed(1)}% vs +${m.buy_hold_return_pct.toFixed(1)}% for doing nothing`
        : `${m.total_return_pct.toFixed(1)}% vs +${m.buy_hold_return_pct.toFixed(1)}% for doing nothing — the extra trading didn't help here`,
    },
    {
      ok: enoughTrades,
      label: 'Enough trades to trust the win rate',
      detail: enoughTrades
        ? `${m.closed_trades} closed trades — a reasonable sample`
        : `only ${m.closed_trades} closed trades — too few to tell luck from a real pattern`,
    },
    {
      ok: positiveExpectancy,
      label: 'Makes money on the average trade',
      detail: positiveExpectancy
        ? `+${m.expectancy_pct.toFixed(2)}% expected return per trade`
        : `${m.expectancy_pct.toFixed(2)}% expected return per trade — losing on average`,
    },
  ]

  const passCount = checks.filter((c) => c.ok).length
  const headline =
    passCount === 3
      ? `✅ This looks worth digging into further`
      : passCount === 0
        ? `🔴 This didn't work here`
        : `⚠️ Mixed result`

  return (
    <div className="card verdict-card">
      <h3>
        In plain terms: {strategyName} on {ticker}
      </h3>
      <p className="verdict-headline">{headline}</p>
      <ul className="verdict-list">
        {checks.map((c, i) => (
          <li key={i} className={c.ok ? 'ok' : 'no'}>
            <span className="verdict-mark">{c.ok ? '✓' : '✗'}</span>
            <span>
              <strong>{c.label}.</strong> {c.detail}.
            </span>
          </li>
        ))}
        <li className="reminder">
          <span className="verdict-mark">?</span>
          <span>
            <strong>Could you stomach the max drawdown?</strong> On your ${initialCapital.toLocaleString('en-US')},
            that worst-point dip of {Math.abs(m.max_drawdown_pct).toFixed(1)}% would have meant
            watching it drop by about $
            {Math.abs((m.max_drawdown_pct / 100) * initialCapital).toLocaleString('en-US', { maximumFractionDigits: 0 })}{' '}
            before it recovered — ask yourself honestly whether you&apos;d have held on with
            real money.
          </span>
        </li>
      </ul>
      <p className="verdict-footer">
        Even a strategy that passes everything here is a reason to keep testing — on a
        different time period, a different asset — not a signal to trade real money.
      </p>
    </div>
  )
}
