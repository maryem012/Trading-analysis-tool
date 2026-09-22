'use client'

import type { StrategyRow } from '@/lib/types'

interface StrategyTableProps {
  rows: StrategyRow[]
  title: string
  showTicker?: boolean
}

function fmtPct(v: number): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

export default function StrategyTable({ rows, title, showTicker = false }: StrategyTableProps) {
  return (
    <div className="table-card card">
      <h3>{title}</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Strategy</th>
              {showTicker && <th>Asset</th>}
              <th title="Growth of the fake starting money, in percent">Return</th>
              <th title="Percent of trades that made money — needs 50+ trades to mean much">Win Rate</th>
              <th title="Return per unit of bumpiness. Above 1 is decent, above 2 is strong.">Sharpe</th>
              <th title="Worst drop from a peak, in percent — how bad the ride got">Max DD</th>
              <th title="Money made on winners ÷ money lost on losers — above 1 means winners outweighed losers">Profit Factor</th>
              <th>Trades</th>
              <th title="Clears ≥50 trades, ≥45% win rate, and positive average return per trade">Edge</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={r.has_edge ? 'edge-row' : undefined}>
                <td>{r.strategy}</td>
                {showTicker && <td>{r.ticker}</td>}
                <td className={r.total_return_pct >= 0 ? 'text-good' : 'text-bad'}>
                  {fmtPct(r.total_return_pct)}
                </td>
                <td>{r.win_rate_pct.toFixed(1)}%</td>
                <td>{r.sharpe_ratio.toFixed(2)}</td>
                <td className="text-bad">{r.max_drawdown_pct.toFixed(2)}%</td>
                <td>{r.profit_factor == null ? '∞' : r.profit_factor.toFixed(2)}</td>
                <td>
                  {r.closed_trades}
                  {r.skipped_zero_size > 0 && (
                    <span
                      className="skip-flag"
                      title={`${r.skipped_zero_size} buy signal(s) skipped — price too high for this risk budget at whole-share sizing`}
                    >
                      {' '}⚠
                    </span>
                  )}
                </td>
                <td>{r.has_edge ? <span className="pill win">✓</span> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
