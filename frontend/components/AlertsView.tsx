'use client'

import { useEffect, useRef, useState } from 'react'
import {
  ApiError, fetchPushStatus, fetchVapidPublicKey, sendTestPush,
  subscribePush, unsubscribePush, updatePushWatchlist,
} from '@/lib/api'
import { getExistingSubscription, isPushSupported, subscribeToPush, unsubscribeFromPush } from '@/lib/push'
import type { StrategyOption, WatchlistItem } from '@/lib/types'
import TickerInput from './TickerInput'

interface AlertsViewProps {
  assets: string[]
  strategies: StrategyOption[]
}

const MAX_WATCHLIST = 20

type Status = 'checking' | 'unsupported' | 'off' | 'on'

export default function AlertsView({ assets, strategies }: AlertsViewProps) {
  const [status, setStatus] = useState<Status>('checking')
  const [subscription, setSubscription] = useState<PushSubscription | null>(null)
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [newTicker, setNewTicker] = useState('SPY')
  const [newStrategy, setNewStrategy] = useState(strategies[0]?.id || 'sma_crossover')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testSent, setTestSent] = useState(false)

  // True once the user has manually enabled/disabled — guards against the
  // mount-time check below resolving *after* that action and clobbering its
  // result with stale data (this genuinely happened: click Enable, the async
  // subscription check from mount lands a moment later and silently flips
  // status back to "off").
  const userActedRef = useRef(false)

  // On load: is push even supported here, and is there already a subscription?
  useEffect(() => {
    if (!isPushSupported()) {
      setStatus('unsupported')
      return
    }
    getExistingSubscription()
      .then(async (sub) => {
        if (userActedRef.current) return
        if (!sub) {
          setStatus('off')
          return
        }
        setSubscription(sub)
        const s = await fetchPushStatus(sub.endpoint)
        if (userActedRef.current) return
        if (!s.subscribed) {
          // The browser still holds a valid push subscription, but the
          // server-side record is gone (e.g. a backend redeploy wiped its
          // local storage — see alerts.py). Silently re-register it rather
          // than surfacing an error or asking the user to re-enable.
          await subscribePush(sub.toJSON() as unknown as PushSubscriptionJSON, [])
          setWatchlist([])
        } else {
          setWatchlist(s.watchlist)
        }
        setStatus('on')
      })
      .catch(() => {
        if (!userActedRef.current) setStatus('off')
      })
  }, [])

  useEffect(() => {
    if (strategies.length && !strategies.some((s) => s.id === newStrategy)) {
      setNewStrategy(strategies[0].id)
    }
  }, [strategies, newStrategy])

  async function handleEnable() {
    userActedRef.current = true
    setBusy(true)
    setError(null)
    try {
      const key = await fetchVapidPublicKey()
      const sub = await subscribeToPush(key)
      await subscribePush(sub.toJSON() as unknown as PushSubscriptionJSON, watchlist)
      setSubscription(sub)
      setStatus('on')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not enable alerts.')
    } finally {
      setBusy(false)
    }
  }

  async function handleDisable() {
    if (!subscription) return
    userActedRef.current = true
    setBusy(true)
    setError(null)
    try {
      await unsubscribePush(subscription.endpoint)
      await unsubscribeFromPush(subscription)
      setSubscription(null)
      setStatus('off')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not disable alerts.')
    } finally {
      setBusy(false)
    }
  }

  async function syncWatchlist(next: WatchlistItem[]) {
    setWatchlist(next)
    if (!subscription) return
    try {
      await updatePushWatchlist(subscription.endpoint, next)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // Server-side record got lost (e.g. a redeploy happened mid-session)
        // — re-register with the browser's still-valid subscription and retry.
        try {
          await subscribePush(subscription.toJSON() as unknown as PushSubscriptionJSON, next)
          return
        } catch {
          // fall through to the generic error below
        }
      }
      setError(e instanceof ApiError ? e.message : 'Could not save the watchlist.')
    }
  }

  function addToWatchlist() {
    if (watchlist.length >= MAX_WATCHLIST) return
    const exists = watchlist.some((w) => w.ticker === newTicker && w.strategy_id === newStrategy)
    if (exists) return
    syncWatchlist([...watchlist, { ticker: newTicker, strategy_id: newStrategy }])
  }

  function removeFromWatchlist(i: number) {
    syncWatchlist(watchlist.filter((_, idx) => idx !== i))
  }

  async function handleTest() {
    if (!subscription) return
    setBusy(true)
    setError(null)
    setTestSent(false)
    try {
      await sendTestPush(subscription.toJSON() as unknown as PushSubscriptionJSON)
      setTestSent(true)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Test notification failed to send.')
    } finally {
      setBusy(false)
    }
  }

  const strategyName = (id: string) => strategies.find((s) => s.id === id)?.name || id

  return (
    <div className="results">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>🔔 Alerts</h2>
        <p className="meta" style={{ marginBottom: 16 }}>
          Get a push notification on this device the moment a strategy on your watchlist
          switches to BUY or SELL — checked roughly every 15 minutes, since the underlying
          price data only updates once a trading day. You won&apos;t be re-notified for a
          signal that&apos;s already been sitting there; only for a fresh change.
        </p>

        {status === 'unsupported' && (
          <div className="error-banner">
            This browser doesn&apos;t support push notifications (or you&apos;re in a mode
            that blocks them, like private/incognito browsing on some browsers). Try a
            regular Chrome, Edge, or Firefox window.
          </div>
        )}

        {status === 'checking' && <p className="meta">Checking…</p>}

        {(status === 'off' || status === 'on') && (
          <>
            {status === 'off' && (
              <button className="run-button" onClick={handleEnable} disabled={busy} style={{ width: 'auto' }}>
                {busy ? <span className="spinner" /> : '🔔'} Enable Alerts
              </button>
            )}

            {status === 'on' && (
              <div className="alert-status">
                <span className="pill win">● Alerts on</span>
                <button className="chip" onClick={handleTest} disabled={busy}>
                  Send test notification
                </button>
                <button className="chip" onClick={handleDisable} disabled={busy}>
                  Turn off
                </button>
                {testSent && <span className="text-good">Sent — check your notifications.</span>}
              </div>
            )}
          </>
        )}

        {error && <div className="error-banner" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      {status === 'on' && (
        <div className="card">
          <h3>Watchlist ({watchlist.length}/{MAX_WATCHLIST})</h3>

          <div className="inline-controls" style={{ marginBottom: 4 }}>
            <div className="field">
              <label htmlFor="alert-ticker">Ticker</label>
              <TickerInput id="alert-ticker" value={newTicker} onChange={setNewTicker} suggestions={assets} />
            </div>
            <div className="field">
              <label htmlFor="alert-strategy">Strategy</label>
              <select id="alert-strategy" value={newStrategy} onChange={(e) => setNewStrategy(e.target.value)}>
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="run-button inline"
              onClick={addToWatchlist}
              disabled={watchlist.length >= MAX_WATCHLIST}
            >
              + Add
            </button>
          </div>

          {watchlist.length === 0 ? (
            <div className="empty-state">
              Nothing watched yet — add a ticker and strategy above to start getting alerts.
            </div>
          ) : (
            <ul className="watchlist">
              {watchlist.map((w, i) => (
                <li key={`${w.ticker}-${w.strategy_id}`}>
                  <span>
                    <strong>{w.ticker}</strong> — {strategyName(w.strategy_id)}
                  </span>
                  <button type="button" className="watchlist-remove" onClick={() => removeFromWatchlist(i)}>
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="card">
        <p className="meta" style={{ margin: 0 }}>
          <strong>Where this actually goes:</strong> the same signal logic as the Market &amp;
          Signals tab — a rule evaluated on the latest closed price bar, not a prediction and
          not investment advice. It works as long as this browser is open somewhere (this tab
          doesn&apos;t need to stay open) — most reliable if you install this site as an app
          (your browser&apos;s menu should have an &ldquo;Install&rdquo; or &ldquo;Add to Home
          Screen&rdquo; option). If you stop this local server, alerts stop too — it&apos;s not
          running anywhere but your own machine right now.
        </p>
      </div>
    </div>
  )
}
