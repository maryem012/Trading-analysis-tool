'use client'

import type { Trade } from '@/lib/types'

interface TradeTableProps {
  trades: Trade[]
}

function fmtMoney(v: number | null): string {
  if (v == null) return '—'
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPct(v: number | null): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

export default function TradeTable({ trades }: TradeTableProps) {
  if (trades.length === 0) {
    return (
      <div className="table-card card">
        <h3>Trade Log</h3>
        <div className="empty-state" style={{ padding: '24px 12px' }}>
          No trades were taken in this window.
        </div>
      </div>
    )
  }

  return (
    <div className="table-card card">
      <h3>Trade Log</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Entry Date</th>
              <th>Entry $</th>
              <th>Exit Date</th>
              <th>Exit $</th>
              <th>P&amp;L $</th>
              <th>Return %</th>
              <th>Days</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => {
              const isOpen = t.status === 'open'
              const isWin = t.profit_loss != null && t.profit_loss > 0
              return (
                <tr key={i} className={isOpen ? 'open-row' : undefined}>
                  <td>{t.entry_date}</td>
                  <td>{fmtMoney(t.entry_price)}</td>
                  <td>{t.exit_date ?? '—'}</td>
                  <td>{fmtMoney(t.exit_price)}</td>
                  <td>{fmtMoney(t.profit_loss)}</td>
                  <td>{fmtPct(t.return_pct)}</td>
                  <td>{t.duration_days != null ? t.duration_days.toFixed(0) : '—'}</td>
                  <td>
                    {isOpen ? (
                      <span className="pill open">Open</span>
                    ) : isWin ? (
                      <span className="pill win">Win</span>
                    ) : (
                      <span className="pill loss">Loss</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
