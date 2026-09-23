'use client'

import type { Signal } from '@/lib/types'

export default function SignalPill({ signal }: { signal: Signal }) {
  const label = signal === 'buy' ? 'BUY' : signal === 'sell' ? 'SELL' : 'HOLD'
  const cls = signal === 'buy' ? 'win' : signal === 'sell' ? 'loss' : 'open'
  return <span className={`pill ${cls}`}>{label}</span>
}
