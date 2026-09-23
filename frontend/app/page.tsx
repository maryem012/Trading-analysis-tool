'use client'

import { useEffect, useState } from 'react'
import TabBar, { type TabId } from '@/components/TabBar'
import BacktestView from '@/components/BacktestView'
import MarketView from '@/components/MarketView'
import CompareView from '@/components/CompareView'
import MatrixView from '@/components/MatrixView'
import AlertsView from '@/components/AlertsView'
import PortfolioView from '@/components/PortfolioView'
import PracticeBanner from '@/components/PracticeBanner'
import GuidePanel from '@/components/GuidePanel'
import { ApiError, fetchAssets, fetchStrategies } from '@/lib/api'
import type { StrategyOption } from '@/lib/types'

export default function Home() {
  const [assets, setAssets] = useState<string[]>([])
  const [strategies, setStrategies] = useState<StrategyOption[]>([])
  const [configError, setConfigError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabId>('backtest')

  useEffect(() => {
    Promise.all([fetchAssets(), fetchStrategies()])
      .then(([a, s]) => {
        setAssets(a)
        setStrategies(s)
      })
      .catch((e) => {
        setConfigError(
          e instanceof ApiError
            ? `Couldn't reach the backtest API: ${e.message}`
            : "Couldn't reach the backtest API. Is it running?"
        )
      })
  }, [])

  return (
    <div className="page">
      <PracticeBanner />

      <div className="page-header">
        <h1>📈 Trading Backtester</h1>
        <p>Run strategies against historical data, compare them, and see live recommendations.</p>
      </div>

      {configError && <div className="error-banner">{configError}</div>}

      <GuidePanel />

      <TabBar active={tab} onChange={setTab} />

      {tab === 'backtest' && <BacktestView assets={assets} strategies={strategies} />}
      {tab === 'market' && <MarketView assets={assets} />}
      {tab === 'compare' && <CompareView assets={assets} />}
      {tab === 'matrix' && <MatrixView assets={assets} />}
      {tab === 'alerts' && <AlertsView assets={assets} strategies={strategies} />}
      {tab === 'portfolio' && <PortfolioView assets={assets} strategies={strategies} />}
    </div>
  )
}
