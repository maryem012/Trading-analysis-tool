'use client'

import type { SignalsResponse, Signal } from '@/lib/types'

interface SignalBannerProps {
  data: SignalsResponse
}

function SignalPill({ signal }: { signal: Signal }) {
  const label = signal === 'buy' ? 'BUY' : signal === 'sell' ? 'SELL' : 'HOLD'
  const cls = signal === 'buy' ? 'win' : signal === 'sell' ? 'loss' : 'open'
  return <span className={`pill ${cls}`}>{label}</span>
}

function StatusBadge({ good, label, activeText, inactiveText }: {
  good: boolean | null
  label: string
  activeText: string
  inactiveText: string
}) {
  if (good == null) {
    return (
      <div className="status-badge neutral">
        <div className="status-label">{label}</div>
        <div className="status-value">—</div>
      </div>
    )
  }
  return (
    <div className={`status-badge ${good ? 'good' : 'neutral'}`}>
      <div className="status-label">{label}</div>
      <div className="status-value">{good ? activeText : inactiveText}</div>
    </div>
  )
}

export default function SignalBanner({ data }: SignalBannerProps) {
  const buyCount = data.recommendations.filter((r) => r.signal === 'buy').length
  const sellCount = data.recommendations.filter((r) => r.signal === 'sell').length

  return (
    <div className="card signal-banner">
      <div className="signal-header">
        <div>
          <h3>
            {data.ticker} — ${data.close.toFixed(2)}
          </h3>
          <p className="meta">As of {data.as_of}</p>
        </div>
        <div className="signal-consensus">
          {buyCount > sellCount && buyCount > 0 && (
            <span className="pill win">⬆ {buyCount} strategies say BUY</span>
          )}
          {sellCount > buyCount && sellCount > 0 && (
            <span className="pill loss">⬇ {sellCount} strategies say SELL</span>
          )}
          {buyCount === sellCount && (
            <span className="pill open">No consensus right now</span>
          )}
        </div>
      </div>

      <div className="status-grid">
        <StatusBadge
          good={data.rsi_overbought}
          label={`RSI (${data.rsi?.toFixed(1) ?? '—'})`}
          activeText="Overbought"
          inactiveText={data.rsi_oversold ? 'Oversold' : 'Neutral'}
        />
        <StatusBadge
          good={data.macd_bullish}
          label="MACD"
          activeText="Bullish"
          inactiveText="Bearish"
        />
        <StatusBadge
          good={data.price_above_sma_50}
          label="Trend vs SMA 50"
          activeText="Above (uptrend)"
          inactiveText="Below (downtrend)"
        />
      </div>

      <div className="rec-grid">
        {data.recommendations.map((r) => (
          <div key={r.strategy_id} className="rec-row">
            <span className="rec-name">{r.strategy_name}</span>
            <SignalPill signal={r.signal} />
          </div>
        ))}
      </div>

      <p className="disclaimer-line">
        These reflect each strategy&apos;s rule evaluated on the latest closed bar — not
        real-time quotes, and not investment advice.
      </p>
    </div>
  )
}
