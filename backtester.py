"""
Backtesting framework — Phase 2

Simulates a trading strategy on historical data and reports performance metrics.

Usage:
    python backtester.py            # demo: SMA crossover on 1 year of AAPL
    python backtester.py MSFT 2

A strategy is just a function: strategy(df, i) -> "buy" | "sell" | "hold"
It looks at df up to and including row i and says what it wants to do.
"""

import sys
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Union

import numpy as np
import pandas as pd
import yfinance as yf

from data_fetcher import DataFetcher

# A strategy takes (dataframe, current row index) and returns a signal string
SignalFunc = Callable[[pd.DataFrame, int], str]

TRADING_DAYS_PER_YEAR = 252


@dataclass
class Trade:
    """A single position — open while exit_price is None, closed once it is filled"""

    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    @property
    def is_open(self) -> bool:
        return self.exit_price is None

    @property
    def cost(self) -> float:
        """Capital tied up when the position was opened"""
        return self.entry_price * self.shares

    @property
    def profit_loss(self) -> Optional[float]:
        """Realised P/L in dollars (None while the trade is open)"""
        if self.is_open:
            return None
        return (self.exit_price - self.entry_price) * self.shares

    @property
    def return_pct(self) -> Optional[float]:
        """Realised return on the position (None while the trade is open)"""
        if self.is_open:
            return None
        return (self.exit_price / self.entry_price - 1) * 100

    @property
    def duration_days(self) -> Optional[int]:
        """Calendar days held (None while the trade is open)"""
        if self.is_open:
            return None
        return (self.exit_date - self.entry_date).days

    @property
    def is_winner(self) -> Optional[bool]:
        if self.is_open:
            return None
        return self.profit_loss > 0

    def unrealized_pl(self, price: float) -> float:
        """Paper P/L of an open position at the given price"""
        return (price - self.entry_price) * self.shares

    def to_dict(self) -> dict:
        return {
            'entry_date': self.entry_date,
            'entry_price': self.entry_price,
            'exit_date': self.exit_date,
            'exit_price': self.exit_price,
            'shares': self.shares,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'profit_loss': self.profit_loss,
            'return_pct': self.return_pct,
            'duration_days': self.duration_days,
            'exit_reason': self.exit_reason if not self.is_open else 'open',
            'status': 'open' if self.is_open else 'closed',
        }


@dataclass
class BacktestResult:
    """Everything a finished backtest produced — trades, equity curve, metrics"""

    ticker: str
    strategy_name: str
    initial_capital: float
    data: pd.DataFrame                      # price data + indicators actually traded on
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    metrics: dict = field(default_factory=dict)

    @property
    def closed_trades(self) -> List[Trade]:
        return [t for t in self.trades if not t.is_open]

    @property
    def open_trades(self) -> List[Trade]:
        return [t for t in self.trades if t.is_open]

    @property
    def final_equity(self) -> float:
        if len(self.equity_curve) == 0:
            return self.initial_capital
        return float(self.equity_curve.iloc[-1])

    def trades_frame(self) -> pd.DataFrame:
        """All trades as a DataFrame (empty frame with the right columns if none)"""
        if not self.trades:
            return pd.DataFrame(columns=[
                'entry_date', 'entry_price', 'exit_date', 'exit_price', 'shares',
                'stop_loss', 'take_profit', 'profit_loss', 'return_pct',
                'duration_days', 'exit_reason', 'status',
            ])
        return pd.DataFrame([t.to_dict() for t in self.trades])

    def drawdown_curve(self) -> pd.Series:
        """Drawdown from the running equity peak, in percent (negative values)"""
        if len(self.equity_curve) == 0:
            return pd.Series(dtype=float)
        peak = self.equity_curve.cummax()
        return (self.equity_curve / peak - 1) * 100

    def metrics_frame(self) -> pd.DataFrame:
        """Metrics formatted for display as a two-column table"""
        m = self.metrics
        rows = [
            ("Total Return", f"{m['total_return_pct']:.2f}%"),
            ("Final Equity", f"${m['final_equity']:,.2f}"),
            ("Buy & Hold Return", f"{m['buy_hold_return_pct']:.2f}%"),
            ("Total Trades", f"{m['total_trades']}"),
            ("Closed / Open", f"{m['closed_trades']} / {m['open_trades']}"),
            ("Win Rate", f"{m['win_rate_pct']:.1f}%"),
            ("Profit Factor", "∞" if math.isinf(m['profit_factor']) else f"{m['profit_factor']:.2f}"),
            ("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}"),
            ("Max Drawdown", f"{m['max_drawdown_pct']:.2f}%"),
            ("Avg Trade Duration", f"{m['avg_trade_duration_days']:.1f} days"),
            ("Avg Win", f"{m['avg_win_pct']:.2f}%"),
            ("Avg Loss", f"{m['avg_loss_pct']:.2f}%"),
            ("Expectancy / Trade", f"{m['expectancy_pct']:.2f}%"),
            ("Gross Profit", f"${m['gross_profit']:,.2f}"),
            ("Gross Loss", f"${m['gross_loss']:,.2f}"),
        ]
        return pd.DataFrame(rows, columns=['Metric', 'Value'])

    def summary(self) -> str:
        """Human-readable report for the terminal"""
        m = self.metrics
        pf = "∞" if math.isinf(m['profit_factor']) else f"{m['profit_factor']:.2f}"
        lines = [
            "=" * 60,
            f"BACKTEST: {self.strategy_name} on {self.ticker}",
            "=" * 60,
            f"Period:            {m['start_date']} → {m['end_date']} ({m['bars']} bars)",
            f"Initial Capital:   ${self.initial_capital:,.2f}",
            f"Final Equity:      ${m['final_equity']:,.2f}",
            "",
            f"Total Return:      {m['total_return_pct']:+.2f}%",
            f"Buy & Hold:        {m['buy_hold_return_pct']:+.2f}%",
            f"Max Drawdown:      {m['max_drawdown_pct']:.2f}%",
            f"Sharpe Ratio:      {m['sharpe_ratio']:.2f}",
            "",
            f"Trades:            {m['total_trades']} ({m['closed_trades']} closed, {m['open_trades']} open)",
            f"Win Rate:          {m['win_rate_pct']:.1f}%  ({m['winning_trades']}W / {m['losing_trades']}L)",
            f"Profit Factor:     {pf}",
            f"Avg Win / Loss:    {m['avg_win_pct']:+.2f}% / {m['avg_loss_pct']:+.2f}%",
            f"Expectancy:        {m['expectancy_pct']:+.2f}% per trade",
            f"Avg Duration:      {m['avg_trade_duration_days']:.1f} days",
        ]
        if m.get('skipped_zero_size'):
            lines.append(
                f"⚠️  Skipped:         {m['skipped_zero_size']} buy signal(s) — position "
                f"size rounded to 0 shares (price too high for this risk budget)"
            )
        lines.append("=" * 60)
        return "\n".join(lines)


class BacktestEngine:
    """
    Runs a signal function over historical bars and tracks the resulting trades.

    Execution model (deliberately conservative, no look-ahead):
      - the signal is computed from a bar's close, and filled at the NEXT bar's open
      - stop-loss / take-profit are checked against each bar's low / high
      - if a bar hits both the stop and the target, the stop is assumed to fill first
      - long-only, one position at a time

    Position size comes from risk_per_trade: the distance to the stop is the risk,
    so shares = (equity * risk_per_trade%) / (entry_price * stop_loss_pct%), capped
    by available cash.
    """

    def __init__(
        self,
        ticker: str = "AAPL",
        start_date: Union[str, datetime, None] = None,
        end_date: Union[str, datetime, None] = None,
        initial_capital: float = 10_000.0,
        risk_per_trade: float = 2.0,
        stop_loss_pct: Optional[float] = 5.0,
        take_profit_pct: Optional[float] = 10.0,
        fractional_shares: bool = False,
        risk_free_rate: float = 0.0,
        warmup_days: int = 250,
    ):
        """
        Args:
            ticker: symbol to test (e.g. "AAPL", "BTC-USD")
            start_date / end_date: test window; defaults to the last year
            initial_capital: starting cash
            risk_per_trade: percent of equity risked per trade (e.g. 2.0 = 2%)
            stop_loss_pct: stop distance below entry, in percent (None = no stop)
            take_profit_pct: target above entry, in percent (None = no target)
            fractional_shares: allow fractional position sizes
            risk_free_rate: annual rate used by the Sharpe ratio
            warmup_days: extra calendar days fetched before start_date so that
                         indicators (SMA 200 etc.) are already warm on day one
        """
        self.ticker = ticker.upper()
        self.end_date = pd.to_datetime(end_date) if end_date else pd.Timestamp(datetime.now().date())
        self.start_date = (
            pd.to_datetime(start_date) if start_date else self.end_date - timedelta(days=365)
        )
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")

        self.initial_capital = float(initial_capital)
        self.risk_per_trade = float(risk_per_trade)
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.fractional_shares = fractional_shares
        self.risk_free_rate = risk_free_rate
        self.warmup_days = warmup_days

        self.data: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------ data

    def load_data(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Fetch OHLCV for the window (plus warmup), add indicators, trim to window.

        Args:
            df: optional pre-fetched OHLCV frame (lowercase columns) to use
                instead of hitting yfinance — handy for tests

        Returns:
            DataFrame indexed by date, indicators included, limited to the
            start_date → end_date window
        """
        if df is None:
            fetch_start = self.start_date - timedelta(days=self.warmup_days)
            print(f"Fetching {self.ticker} from {fetch_start.date()} to {self.end_date.date()}...")
            df = yf.download(
                self.ticker,
                start=fetch_start,
                end=self.end_date,
                progress=False,
                auto_adjust=True,
            )
            if df is None or len(df) == 0:
                raise ValueError(f"No data returned for {self.ticker}")
            df = DataFetcher.normalize_columns(df)
        else:
            df = DataFetcher.normalize_columns(df.copy())

        # Reuse the Phase 1 indicator set so strategies see the same columns
        # the dashboard shows
        full = DataFetcher(self.ticker).add_indicators(df)

        # Drop the warmup rows — they only existed to prime the moving averages.
        # Keep the untrimmed frame reachable via .attrs so a strategy that adds
        # its own indicator column on demand (e.g. an arbitrary SMA period for a
        # parameter sweep) can compute it with the warmup rows included instead
        # of getting NaNs for the first `period` bars of the test window itself.
        trimmed = full.loc[(full.index >= self.start_date) & (full.index <= self.end_date)]
        if len(trimmed) < 2:
            raise ValueError(
                f"Only {len(trimmed)} bars in {self.start_date.date()}–{self.end_date.date()}; "
                "widen the date range"
            )
        trimmed.attrs['_full_data'] = full

        self.data = trimmed
        print(f"Loaded {len(trimmed)} bars for backtest")
        return trimmed

    # -------------------------------------------------------------- simulate

    def run(self, strategy: SignalFunc, strategy_name: Optional[str] = None) -> BacktestResult:
        """
        Simulate the strategy bar by bar.

        Args:
            strategy: function (df, i) -> "buy" | "sell" | "hold"
            strategy_name: label for reports (defaults to the function name)

        Returns:
            BacktestResult with trades, equity curve and metrics
        """
        df = self.data if self.data is not None else self.load_data()
        name = strategy_name or getattr(strategy, '__name__', 'strategy')

        cash = self.initial_capital
        position: Optional[Trade] = None
        trades: List[Trade] = []
        equity_values: List[float] = []
        pending: Optional[str] = None       # order to fill at the next bar's open
        skipped_zero_size = 0               # buy signals dropped: risk budget rounds to 0 shares

        for i in range(len(df)):
            bar = df.iloc[i]
            date = df.index[i]
            bar_open = float(bar['open'])

            # 1. Fill yesterday's order at today's open
            if pending == 'buy' and position is None:
                # Flat here, so cash is the whole account equity
                shares = self._position_size(cash, cash, bar_open)
                if shares > 0:
                    position = Trade(
                        entry_date=date,
                        entry_price=bar_open,
                        shares=shares,
                        stop_loss=self._stop_price(bar_open),
                        take_profit=self._target_price(bar_open),
                    )
                    cash -= position.cost
                    trades.append(position)
                else:
                    # Not "no signal" — a real buy signal that the risk budget
                    # can't afford even one share of at whole-share sizing.
                    # Silent zero-trade runs are indistinguishable from "the
                    # strategy never fired" otherwise, which has bitten this
                    # project before on expensive assets (BTC-USD) — surface it.
                    skipped_zero_size += 1
            elif pending == 'sell' and position is not None:
                cash += self._close(position, date, bar_open, 'signal')
                position = None
            pending = None

            # 2. Stop-loss / take-profit can still trigger later in the same bar
            if position is not None:
                exit_price, reason = self._check_bar_exit(position, bar)
                if exit_price is not None:
                    cash += self._close(position, date, exit_price, reason)
                    position = None

            # 3. Mark the account to market on this bar's close
            close = float(bar['close'])
            equity_values.append(cash + (position.shares * close if position else 0.0))

            # 4. Ask the strategy what to do, to be filled on the next open
            if i < len(df) - 1:
                signal = self._read_signal(strategy, df, i)
                if signal == 'buy' and position is None:
                    pending = 'buy'
                elif signal == 'sell' and position is not None:
                    pending = 'sell'

        if skipped_zero_size > 0:
            print(
                f"⚠️  {skipped_zero_size} buy signal(s) on {self.ticker} skipped — "
                f"risk_per_trade={self.risk_per_trade}% of ${self.initial_capital:,.0f} "
                f"can't afford 1 whole share at this price with stop_loss_pct="
                f"{self.stop_loss_pct}%. Raise initial_capital/risk_per_trade, "
                f"lower stop_loss_pct, or set fractional_shares=True."
            )

        equity_curve = pd.Series(equity_values, index=df.index, name='equity')
        metrics = compute_metrics(
            equity_curve=equity_curve,
            trades=trades,
            initial_capital=self.initial_capital,
            price=df['close'],
            risk_free_rate=self.risk_free_rate,
            skipped_zero_size=skipped_zero_size,
        )

        return BacktestResult(
            ticker=self.ticker,
            strategy_name=name,
            initial_capital=self.initial_capital,
            data=df,
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
        )

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _read_signal(strategy: SignalFunc, df: pd.DataFrame, i: int) -> str:
        """Call the strategy and normalise whatever it returns to a known signal"""
        signal = strategy(df, i)
        if signal is None:
            return 'hold'
        signal = str(signal).strip().lower()
        return signal if signal in ('buy', 'sell', 'hold') else 'hold'

    def _stop_price(self, entry_price: float) -> Optional[float]:
        if self.stop_loss_pct is None:
            return None
        return entry_price * (1 - self.stop_loss_pct / 100)

    def _target_price(self, entry_price: float) -> Optional[float]:
        if self.take_profit_pct is None:
            return None
        return entry_price * (1 + self.take_profit_pct / 100)

    def _position_size(self, equity: float, cash: float, entry_price: float) -> float:
        """Shares to buy, from the risk budget and capped by available cash"""
        if entry_price <= 0 or cash <= 0:
            return 0.0

        risk_amount = equity * self.risk_per_trade / 100
        if self.stop_loss_pct:
            stop_distance = entry_price * self.stop_loss_pct / 100
            shares = risk_amount / stop_distance
        else:
            # No stop means no risk distance to size against — use all the cash
            shares = cash / entry_price

        shares = min(shares, cash / entry_price)
        if not self.fractional_shares:
            shares = math.floor(shares)
        return max(shares, 0.0)

    def _check_bar_exit(self, trade: Trade, bar: pd.Series):
        """Did this bar hit the stop or the target? Returns (price, reason)"""
        low, high, bar_open = float(bar['low']), float(bar['high']), float(bar['open'])

        if trade.stop_loss is not None and low <= trade.stop_loss:
            # A gap through the stop fills at the open, not at the stop price
            return min(trade.stop_loss, bar_open), 'stop_loss'
        if trade.take_profit is not None and high >= trade.take_profit:
            return max(trade.take_profit, bar_open), 'take_profit'
        return None, None

    @staticmethod
    def _close(trade: Trade, date, price: float, reason: str) -> float:
        """Close a trade and return the proceeds to add back to cash"""
        trade.exit_date = date
        trade.exit_price = price
        trade.exit_reason = reason
        return price * trade.shares


# ----------------------------------------------------------------- metrics


def compute_metrics(
    equity_curve: pd.Series,
    trades: List[Trade],
    initial_capital: float,
    price: Optional[pd.Series] = None,
    risk_free_rate: float = 0.0,
    skipped_zero_size: int = 0,
) -> dict:
    """
    Performance stats for a finished run.

    Returns-based metrics (total return, Sharpe, drawdown) come from the equity
    curve, which marks any still-open position to market. Trade stats (win rate,
    profit factor, durations) only count closed trades.
    """
    closed = [t for t in trades if not t.is_open]
    open_trades = [t for t in trades if t.is_open]

    final_equity = float(equity_curve.iloc[-1]) if len(equity_curve) else initial_capital
    total_return_pct = (final_equity / initial_capital - 1) * 100

    wins = [t for t in closed if t.profit_loss > 0]
    losses = [t for t in closed if t.profit_loss <= 0]
    gross_profit = sum(t.profit_loss for t in wins)
    gross_loss = abs(sum(t.profit_loss for t in losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float('inf') if gross_profit > 0 else 0.0

    returns = equity_curve.pct_change().dropna() if len(equity_curve) > 1 else pd.Series(dtype=float)
    if len(returns) > 1 and returns.std() > 0:
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        sharpe = (returns.mean() - daily_rf) / returns.std() * math.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        sharpe = 0.0

    if len(equity_curve):
        drawdown = equity_curve / equity_curve.cummax() - 1
        max_drawdown_pct = float(drawdown.min()) * 100
    else:
        max_drawdown_pct = 0.0

    durations = [t.duration_days for t in closed]
    trade_returns = [t.return_pct for t in closed]

    buy_hold_return_pct = 0.0
    if price is not None and len(price) > 1:
        buy_hold_return_pct = (float(price.iloc[-1]) / float(price.iloc[0]) - 1) * 100

    return {
        'start_date': equity_curve.index[0].date() if len(equity_curve) else None,
        'end_date': equity_curve.index[-1].date() if len(equity_curve) else None,
        'bars': len(equity_curve),
        'initial_capital': initial_capital,
        'final_equity': final_equity,
        'total_return_pct': total_return_pct,
        'buy_hold_return_pct': buy_hold_return_pct,
        'total_trades': len(trades),
        'closed_trades': len(closed),
        'open_trades': len(open_trades),
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate_pct': (len(wins) / len(closed) * 100) if closed else 0.0,
        'profit_factor': profit_factor,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'net_profit': gross_profit - gross_loss,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_drawdown_pct,
        'avg_trade_duration_days': float(np.mean(durations)) if durations else 0.0,
        'avg_win_pct': float(np.mean([t.return_pct for t in wins])) if wins else 0.0,
        'avg_loss_pct': float(np.mean([t.return_pct for t in losses])) if losses else 0.0,
        'expectancy_pct': float(np.mean(trade_returns)) if trade_returns else 0.0,
        'best_trade_pct': max(trade_returns) if trade_returns else 0.0,
        'worst_trade_pct': min(trade_returns) if trade_returns else 0.0,
        # Buy signals that fired but whose risk-based position size rounded
        # down to 0 whole shares (price too high relative to the risk budget)
        # — a non-zero count here means "0 trades" was NOT "no signal"
        'skipped_zero_size': skipped_zero_size,
    }


# ---------------------------------------------------------------- strategies


def sma_crossover(df: pd.DataFrame, i: int) -> str:
    """
    Example strategy: SMA 20 / SMA 50 crossover.

    Buy when SMA 20 crosses above SMA 50 (golden cross), sell when it crosses
    back below (death cross). Only the crossing bar fires — no repeat signals
    while the trend is already in place.
    """
    if i < 1:
        return 'hold'

    fast_now, slow_now = df['sma_20'].iloc[i], df['sma_50'].iloc[i]
    fast_prev, slow_prev = df['sma_20'].iloc[i - 1], df['sma_50'].iloc[i - 1]

    if pd.isna([fast_now, slow_now, fast_prev, slow_prev]).any():
        return 'hold'

    if fast_prev <= slow_prev and fast_now > slow_now:
        return 'buy'
    if fast_prev >= slow_prev and fast_now < slow_now:
        return 'sell'
    return 'hold'


def make_sma_crossover(fast: int = 20, slow: int = 50) -> SignalFunc:
    """
    Build an SMA crossover strategy over arbitrary periods.

    The Phase 1 indicator set only precomputes SMA 20/50/200, so for any other
    period the strategy adds the column itself, once, the first time it's
    called — every bar shares the same DataFrame instance for one backtest
    run, so the column persists and never gets recomputed per bar. If the
    engine stashed the pre-trim frame (see BacktestEngine.load_data), the
    rolling mean is computed there so the warmup rows are already included
    instead of leaving the first `period` bars of the test window as NaN.
    """
    fast_col, slow_col = f'sma_{fast}', f'sma_{slow}'

    def _ensure(df: pd.DataFrame, col: str, period: int) -> None:
        if col in df.columns:
            return
        full = df.attrs.get('_full_data')
        if full is not None:
            if col not in full.columns:
                full[col] = full['close'].rolling(window=period).mean()
            df[col] = full[col].reindex(df.index)
        else:
            df[col] = df['close'].rolling(window=period).mean()

    def strategy(df: pd.DataFrame, i: int) -> str:
        _ensure(df, fast_col, fast)
        _ensure(df, slow_col, slow)

        if i < 1:
            return 'hold'
        f_now, s_now = df[fast_col].iloc[i], df[slow_col].iloc[i]
        f_prev, s_prev = df[fast_col].iloc[i - 1], df[slow_col].iloc[i - 1]
        if pd.isna([f_now, s_now, f_prev, s_prev]).any():
            return 'hold'
        if f_prev <= s_prev and f_now > s_now:
            return 'buy'
        if f_prev >= s_prev and f_now < s_now:
            return 'sell'
        return 'hold'

    strategy.__name__ = f'sma_{fast}_{slow}_crossover'
    return strategy


def rsi_reversion(df: pd.DataFrame, i: int, oversold: float = 30, overbought: float = 70) -> str:
    """Second example: buy when RSI leaves oversold, sell when it leaves overbought"""
    if i < 1:
        return 'hold'

    rsi_now, rsi_prev = df['rsi'].iloc[i], df['rsi'].iloc[i - 1]
    if pd.isna([rsi_now, rsi_prev]).any():
        return 'hold'

    if rsi_prev < oversold <= rsi_now:
        return 'buy'
    if rsi_prev > overbought >= rsi_now:
        return 'sell'
    return 'hold'


def make_rsi_reversion(oversold: float = 30, overbought: float = 70) -> SignalFunc:
    """Build an RSI reversion strategy over arbitrary thresholds (for parameter sweeps)"""

    def strategy(df: pd.DataFrame, i: int) -> str:
        return rsi_reversion(df, i, oversold=oversold, overbought=overbought)

    strategy.__name__ = f'rsi_{oversold:g}_{overbought:g}_reversion'
    return strategy


def macd_crossover(df: pd.DataFrame, i: int) -> str:
    """Buy when the MACD line crosses above its signal line, sell on the cross back below"""
    if i < 1:
        return 'hold'

    macd_now, sig_now = df['macd'].iloc[i], df['macd_signal'].iloc[i]
    macd_prev, sig_prev = df['macd'].iloc[i - 1], df['macd_signal'].iloc[i - 1]

    if pd.isna([macd_now, sig_now, macd_prev, sig_prev]).any():
        return 'hold'

    if macd_prev <= sig_prev and macd_now > sig_now:
        return 'buy'
    if macd_prev >= sig_prev and macd_now < sig_now:
        return 'sell'
    return 'hold'


def bollinger_reversion(df: pd.DataFrame, i: int) -> str:
    """Mean reversion off the bands: buy a bounce off the lower band, sell a fade off the upper"""
    if i < 1:
        return 'hold'

    close_now, close_prev = df['close'].iloc[i], df['close'].iloc[i - 1]
    lower_now, lower_prev = df['bb_lower'].iloc[i], df['bb_lower'].iloc[i - 1]
    upper_now, upper_prev = df['bb_upper'].iloc[i], df['bb_upper'].iloc[i - 1]

    if pd.isna([close_now, close_prev, lower_now, lower_prev, upper_now, upper_prev]).any():
        return 'hold'

    if close_prev <= lower_prev and close_now > lower_now:
        return 'buy'
    if close_prev >= upper_prev and close_now < upper_now:
        return 'sell'
    return 'hold'


STRATEGIES = {
    'SMA 20/50 Crossover': sma_crossover,
    'SMA 50/200 Crossover': make_sma_crossover(50, 200),
    'RSI Mean Reversion': rsi_reversion,
    'MACD Crossover': macd_crossover,
    'Bollinger Reversion': bollinger_reversion,
}


# --------------------------------------------------------------------- demo


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    years = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

    end = pd.Timestamp(datetime.now().date())
    start = end - timedelta(days=int(365 * years))

    print(f"\n🔬 Backtesting SMA crossover on {ticker} ({years:g}y)\n")

    engine = BacktestEngine(
        ticker=ticker,
        start_date=start,
        end_date=end,
        initial_capital=10_000,
        risk_per_trade=2.0,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
    )
    result = engine.run(sma_crossover, strategy_name="SMA 20/50 Crossover")

    print()
    print(result.summary())

    trades = result.trades_frame()
    print("\nTRADE LOG")
    print("-" * 60)
    if trades.empty:
        print("No trades were taken — the strategy never crossed over in this window.")
    else:
        show = trades.copy()
        for col in ('entry_date', 'exit_date'):
            show[col] = pd.to_datetime(show[col]).dt.date
        cols = ['entry_date', 'entry_price', 'exit_date', 'exit_price', 'shares',
                'profit_loss', 'return_pct', 'duration_days', 'exit_reason']
        print(show[cols].round(2).to_string(index=False))

    print("\n💡 Run `streamlit run dashboard.py` for the charted version.\n")


if __name__ == "__main__":
    main()
