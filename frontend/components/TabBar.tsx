'use client'

export type TabId = 'backtest' | 'market' | 'compare' | 'matrix' | 'alerts'

const TABS: { id: TabId; label: string; hint: string }[] = [
  { id: 'backtest', label: '🔁 Backtest', hint: 'Test one strategy on one asset over time' },
  { id: 'market', label: '📊 Market & Signals', hint: 'Current price, indicators, and what each strategy says to do right now' },
  { id: 'compare', label: '⚖️ Compare Strategies', hint: 'Rank every strategy against each other on one asset' },
  { id: 'matrix', label: '🗺️ Asset Matrix', hint: 'See which strategies work best on which assets' },
  { id: 'alerts', label: '🔔 Alerts', hint: 'Get a push notification when a signal changes' },
]

interface TabBarProps {
  active: TabId
  onChange: (tab: TabId) => void
}

export default function TabBar({ active, onChange }: TabBarProps) {
  return (
    <div className="tab-bar">
      {TABS.map((t) => (
        <button
          key={t.id}
          className={`tab-button${active === t.id ? ' active' : ''}`}
          onClick={() => onChange(t.id)}
          title={t.hint}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}
