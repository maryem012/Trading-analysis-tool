import type {
  Account,
  AutoTradeItem,
  BacktestResponse,
  BrokerOrder,
  BrokerStatus,
  CompareResponse,
  MatrixResponse,
  Position,
  PriceHistoryResponse,
  PushStatus,
  SignalsResponse,
  StrategyOption,
  WatchlistItem,
} from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg).join(', ')
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(detail, res.status)
  }
  return res.json()
}

export async function fetchStrategies(): Promise<StrategyOption[]> {
  const res = await fetch(`${API_URL}/api/strategies`)
  return handle(res)
}

export async function fetchAssets(): Promise<string[]> {
  const res = await fetch(`${API_URL}/api/assets`)
  return handle(res)
}

export async function runBacktest(params: {
  ticker: string
  strategy: string
  days: number
  initial_capital?: number
  risk_per_trade?: number
  stop_loss_pct?: number
  take_profit_pct?: number
}): Promise<BacktestResponse> {
  const res = await fetch(`${API_URL}/api/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return handle(res)
}

export async function fetchPriceHistory(ticker: string, days: number): Promise<PriceHistoryResponse> {
  const res = await fetch(`${API_URL}/api/price-history?ticker=${encodeURIComponent(ticker)}&days=${days}`)
  return handle(res)
}

export async function fetchSignals(ticker: string, days = 365): Promise<SignalsResponse> {
  const res = await fetch(`${API_URL}/api/signals?ticker=${encodeURIComponent(ticker)}&days=${days}`)
  return handle(res)
}

export async function runCompare(params: {
  ticker: string
  days: number
  strategy_ids?: string[]
}): Promise<CompareResponse> {
  const res = await fetch(`${API_URL}/api/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return handle(res)
}

export async function runMatrix(params: {
  tickers?: string[]
  years: number
  strategy_ids?: string[]
}): Promise<MatrixResponse> {
  const res = await fetch(`${API_URL}/api/matrix`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return handle(res)
}

export async function fetchVapidPublicKey(): Promise<string> {
  const res = await fetch(`${API_URL}/api/push/vapid-public-key`)
  const data = await handle<{ publicKey: string }>(res)
  return data.publicKey
}

export async function subscribePush(
  subscription: PushSubscriptionJSON,
  watchlist: WatchlistItem[]
): Promise<{ status: string; watching: number }> {
  const res = await fetch(`${API_URL}/api/push/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subscription, watchlist }),
  })
  return handle(res)
}

export async function unsubscribePush(endpoint: string): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/api/push/unsubscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint }),
  })
  return handle(res)
}

export async function updatePushWatchlist(
  endpoint: string,
  watchlist: WatchlistItem[]
): Promise<{ status: string; watching: number }> {
  const res = await fetch(`${API_URL}/api/push/watchlist`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint, watchlist }),
  })
  return handle(res)
}

export async function fetchPushStatus(endpoint: string): Promise<PushStatus> {
  const res = await fetch(`${API_URL}/api/push/status?endpoint=${encodeURIComponent(endpoint)}`)
  return handle(res)
}

export async function sendTestPush(
  subscription: PushSubscriptionJSON
): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/api/push/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subscription }),
  })
  return handle(res)
}

export async function fetchBrokerStatus(): Promise<BrokerStatus> {
  const res = await fetch(`${API_URL}/api/broker/status`)
  return handle(res)
}

export async function fetchAccount(): Promise<Account> {
  const res = await fetch(`${API_URL}/api/broker/account`)
  return handle(res)
}

export async function fetchPositions(): Promise<Position[]> {
  const res = await fetch(`${API_URL}/api/broker/positions`)
  return handle(res)
}

export async function fetchOrders(limit = 50): Promise<BrokerOrder[]> {
  const res = await fetch(`${API_URL}/api/broker/orders?limit=${limit}`)
  return handle(res)
}

export async function placeOrder(params: {
  ticker: string
  side: 'buy' | 'sell'
  notional: number
}): Promise<BrokerOrder> {
  const res = await fetch(`${API_URL}/api/broker/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return handle(res)
}

export async function closePosition(ticker: string): Promise<BrokerOrder> {
  const res = await fetch(`${API_URL}/api/broker/positions/${encodeURIComponent(ticker)}/close`, {
    method: 'POST',
  })
  return handle(res)
}

export async function fetchAutoTrade(): Promise<AutoTradeItem[]> {
  const res = await fetch(`${API_URL}/api/broker/auto-trade`)
  const data = await handle<{ items: AutoTradeItem[] }>(res)
  return data.items
}

export async function updateAutoTrade(items: AutoTradeItem[]): Promise<AutoTradeItem[]> {
  const res = await fetch(`${API_URL}/api/broker/auto-trade`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  const data = await handle<{ items: AutoTradeItem[] }>(res)
  return data.items
}

export { ApiError }
