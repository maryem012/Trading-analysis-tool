export interface Metrics {
  start_date: string
  end_date: string
  bars: number
  initial_capital: number
  final_equity: number
  total_return_pct: number
  buy_hold_return_pct: number
  total_trades: number
  closed_trades: number
  open_trades: number
  winning_trades: number
  losing_trades: number
  win_rate_pct: number
  profit_factor: number | null
  gross_profit: number
  gross_loss: number
  net_profit: number
  sharpe_ratio: number
  max_drawdown_pct: number
  avg_trade_duration_days: number
  avg_win_pct: number
  avg_loss_pct: number
  expectancy_pct: number
  best_trade_pct: number
  worst_trade_pct: number
}

export interface Trade {
  entry_date: string
  entry_price: number
  exit_date: string | null
  exit_price: number | null
  shares: number
  stop_loss: number | null
  take_profit: number | null
  profit_loss: number | null
  return_pct: number | null
  duration_days: number | null
  exit_reason: string
  status: 'open' | 'closed'
}

export interface EquityPoint {
  date: string
  equity: number | null
}

export interface BacktestResponse {
  ticker: string
  strategy: string
  strategy_id: string
  days: number
  initial_capital: number
  metrics: Metrics
  trades: Trade[]
  equity_curve: EquityPoint[]
  buy_hold_curve: EquityPoint[]
}

export interface StrategyOption {
  id: string
  name: string
}

export interface PriceBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  sma_20: number | null
  sma_50: number | null
  sma_200: number | null
  bb_upper: number | null
  bb_lower: number | null
  rsi: number | null
  macd: number | null
  macd_signal: number | null
}

export interface PriceHistoryResponse {
  ticker: string
  days: number
  bars: PriceBar[]
}

export type Signal = 'buy' | 'sell' | 'hold'

export interface Recommendation {
  strategy_id: string
  strategy_name: string
  signal: Signal
  reason?: string
}

export interface SignalsResponse {
  ticker: string
  as_of: string
  close: number
  rsi: number | null
  macd: number | null
  macd_signal: number | null
  sma_20: number | null
  sma_50: number | null
  sma_200: number | null
  rsi_overbought: boolean | null
  rsi_oversold: boolean | null
  macd_bullish: boolean | null
  price_above_sma_50: boolean | null
  recommendations: Recommendation[]
}

export interface StrategyRow {
  strategy: string
  strategy_id: string
  ticker: string
  total_trades: number
  closed_trades: number
  open_trades: number
  win_rate_pct: number
  total_return_pct: number
  buy_hold_return_pct: number
  sharpe_ratio: number
  max_drawdown_pct: number
  profit_factor: number | null
  expectancy_pct: number
  avg_trade_duration_days: number
  has_edge: boolean
  skipped_zero_size: number
}

export interface CompareResponse {
  ticker: string
  start_date: string
  end_date: string
  rows: StrategyRow[]
}

export interface MatrixRow extends StrategyRow {
  years: number
}

export interface MatrixResponse {
  rows: MatrixRow[]
}

export interface WatchlistItem {
  ticker: string
  strategy_id: string
}

export interface PushStatus {
  subscribed: boolean
  watchlist: WatchlistItem[]
}

export interface BrokerStatus {
  configured: boolean
  paper: boolean
}

export interface Account {
  status: string
  cash: number
  equity: number
  buying_power: number
  portfolio_value: number
}

export interface Position {
  ticker: string
  qty: number
  avg_entry_price: number
  current_price: number
  market_value: number
  unrealized_pl: number
  unrealized_plpc: number
}

export interface BrokerOrder {
  id: string
  ticker: string
  side: 'buy' | 'sell' | null
  qty: number | null
  notional: number | null
  status: string | null
  submitted_at: string | null
  filled_avg_price: number | null
}
