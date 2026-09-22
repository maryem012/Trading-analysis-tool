"""
Strategy Laboratory & Optimization — Phase 3

Runs many backtests against each other instead of one at a time: compares
strategies head to head, sweeps parameters to find good settings, tests across
assets and timeframes, combines signals with AND/OR logic, and writes an HTML
report of what actually held up.

Usage:
    python strategy_lab.py           # runs the full demo and writes reports/strategy_lab.html

IMPORTANT — read this before trusting any table this module prints:
This is a research tool for narrowing down what's worth investigating further,
not a verdict on what to trade. A strategy that "wins" here was tuned and
tested on the same historical data (some data leakage is unavoidable in a
single-repo demo like this one), so:
  - A parameter sweep's "best" combination is the one that fit this particular
    history best — that is mild overfitting by construction. Sanity-check it
    on a period or asset it wasn't chosen from before trusting it.
  - Five wins out of eight trades is not a 62% win rate you can rely on — see
    `meets_edge_criteria()` and the trade-count gate on every ranking.
  - No commissions, slippage, or borrow costs are modeled anywhere in here.
"""

import itertools
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import yfinance as yf

from backtester import BacktestEngine, BacktestResult, SignalFunc, STRATEGIES
from data_fetcher import DataFetcher
from plots import heatmap_figure, ranking_bar_chart

CACHE_DIR = Path(__file__).parent / ".cache"
DEFAULT_WARMUP_DAYS = 400   # covers SMA 200 with room to spare for sweeps that go longer

# In-memory cache, keyed by (ticker, start, end, warmup) — reused across every
# strategy / parameter combo that shares a window, so a 20-combination sweep
# hits yfinance once, not 20 times
_MEMORY_CACHE: Dict[tuple, pd.DataFrame] = {}


# ============================================================================
# Data caching
# ============================================================================

def get_price_data(ticker: str, start_date, end_date,
                    warmup_days: int = DEFAULT_WARMUP_DAYS,
                    use_disk_cache: bool = True) -> pd.DataFrame:
    """
    Fetch raw OHLCV for one (ticker, window), memoized in memory and on disk.

    Every comparison/sweep/matrix function in this module routes through here,
    so running several analyses over the same ticker and date range only ever
    downloads once.
    """
    ticker = ticker.upper()
    start_date, end_date = pd.Timestamp(start_date), pd.Timestamp(end_date)
    key = (ticker, start_date.date(), end_date.date(), warmup_days)
    if key in _MEMORY_CACHE:
        return _MEMORY_CACHE[key].copy()

    cache_file = CACHE_DIR / f"{ticker}_{start_date.date()}_{end_date.date()}_{warmup_days}.csv"
    if use_disk_cache and cache_file.exists():
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        _MEMORY_CACHE[key] = df
        return df.copy()

    fetch_start = start_date - timedelta(days=warmup_days)
    print(f"  Fetching {ticker} ({fetch_start.date()} → {end_date.date()})...")
    raw = yf.download(ticker, start=fetch_start, end=end_date, progress=False, auto_adjust=True)
    if raw is None or len(raw) == 0:
        raise ValueError(f"No data returned for {ticker}")
    df = DataFetcher.normalize_columns(raw)

    if use_disk_cache:
        CACHE_DIR.mkdir(exist_ok=True)
        df.to_csv(cache_file)

    _MEMORY_CACHE[key] = df
    return df.copy()


def _run_one(strategy: SignalFunc, strategy_name: str, ticker: str, start_date, end_date,
             engine_kwargs: dict, warmup_days: int = DEFAULT_WARMUP_DAYS) -> BacktestResult:
    """Build an engine against cached data and run one strategy on it."""
    raw = get_price_data(ticker, start_date, end_date, warmup_days=warmup_days)
    engine = BacktestEngine(ticker=ticker, start_date=start_date, end_date=end_date,
                             warmup_days=warmup_days, **engine_kwargs)
    engine.load_data(raw)
    return engine.run(strategy, strategy_name=strategy_name)


# ============================================================================
# Edge criteria
# ============================================================================

def meets_edge_criteria(metrics: dict, min_trades: int = 50, min_win_rate: float = 45.0,
                         min_expectancy: float = 0.0) -> bool:
    """
    Does a result clear the bar for "worth a closer look"?

    Defaults match the Phase 3 brief: 50+ closed trades (so the win rate means
    something), win rate above 45%, and positive expectancy per trade. All
    three, not any one — a great win rate on 6 trades is noise, and a 45%+ win
    rate with negative expectancy is still a loser.
    """
    return (
        metrics['closed_trades'] >= min_trades
        and metrics['win_rate_pct'] >= min_win_rate
        and metrics['expectancy_pct'] > min_expectancy
    )


def _metrics_row(result: BacktestResult, **extra) -> dict:
    """Flatten a BacktestResult's metrics into one table row, tagged with extra columns."""
    m = result.metrics
    row = {
        **extra,
        'total_trades': m['total_trades'],
        'closed_trades': m['closed_trades'],
        'open_trades': m['open_trades'],
        'win_rate_pct': m['win_rate_pct'],
        'total_return_pct': m['total_return_pct'],
        'buy_hold_return_pct': m['buy_hold_return_pct'],
        'sharpe_ratio': m['sharpe_ratio'],
        'max_drawdown_pct': m['max_drawdown_pct'],
        'profit_factor': m['profit_factor'],
        'expectancy_pct': m['expectancy_pct'],
        'avg_trade_duration_days': m['avg_trade_duration_days'],
        # A row of zeros here can mean either "the strategy never signaled" or
        # "it signaled but the risk budget couldn't afford 1 whole share at
        # this price" (e.g. BTC-USD at $60k+ with $10k capital) — this field
        # tells the two apart instead of leaving a silent, misleading zero.
        'skipped_zero_size': m.get('skipped_zero_size', 0),
    }
    row['has_edge'] = meets_edge_criteria(m)
    return row


def _edge_mask(df: pd.DataFrame, edge_kwargs: Optional[dict]) -> pd.Series:
    """The precomputed 'has_edge' column, or a fresh mask if custom thresholds are given"""
    if not edge_kwargs:
        return df['has_edge']
    return df.apply(lambda r: meets_edge_criteria(r.to_dict(), **edge_kwargs), axis=1)


def pool_trades(results: Sequence[BacktestResult]) -> dict:
    """
    Combine closed trades from several backtests of the *same* strategy (e.g.
    run across different assets or timeframes) into one pooled sample.

    A strategy that only manages 15 trades on any single asset over a few
    years can still be judged fairly once pooled across several largely
    independent assets — that's standard practice for getting a meaningful
    sample size out of a short backtest history, not a trick to pass the bar.
    It's still not free of correlation (equities move together in a crash),
    so treat pooled results as better evidence than one asset alone, not as
    50 fully independent coin flips.
    """
    trades = [t for r in results for t in r.closed_trades]
    wins = [t for t in trades if t.profit_loss > 0]
    losses = [t for t in trades if t.profit_loss <= 0]
    gross_profit = sum(t.profit_loss for t in wins)
    gross_loss = abs(sum(t.profit_loss for t in losses))
    trade_returns = [t.return_pct for t in trades]

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float('inf') if gross_profit > 0 else 0.0

    return {
        'closed_trades': len(trades),
        'win_rate_pct': (len(wins) / len(trades) * 100) if trades else 0.0,
        'profit_factor': profit_factor,
        'expectancy_pct': float(np.mean(trade_returns)) if trade_returns else 0.0,
        'avg_trade_duration_days': float(np.mean([t.duration_days for t in trades])) if trades else 0.0,
        'sources': len(results),
    }


def pooled_edge_table(matrix: MatrixResult, min_trades: int = 50, min_win_rate: float = 45.0,
                       min_expectancy: float = 0.0) -> pd.DataFrame:
    """
    For each strategy in a MatrixResult, pool its closed trades across every
    asset/timeframe it was run on and check the edge bar against that pooled
    sample — the search the module docstring recommends when no single asset
    reaches 50 trades on its own.
    """
    rows = []
    strategy_names = sorted({name for (name, _, _) in matrix.results.keys()})
    for name in strategy_names:
        by_strategy = [r for (s, _, _), r in matrix.results.items() if s == name]
        pooled = pool_trades(by_strategy)
        pooled['strategy'] = name
        pooled['has_edge'] = meets_edge_criteria(pooled, min_trades, min_win_rate, min_expectancy)
        rows.append(pooled)
    cols = ['strategy', 'sources', 'closed_trades', 'win_rate_pct', 'profit_factor',
            'expectancy_pct', 'avg_trade_duration_days', 'has_edge']
    return pd.DataFrame(rows)[cols].sort_values('expectancy_pct', ascending=False).reset_index(drop=True)


# ============================================================================
# 1. Strategy comparison
# ============================================================================

@dataclass
class StrategyComparison:
    ticker: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    table: pd.DataFrame
    results: Dict[str, BacktestResult] = field(default_factory=dict)

    def ranked(self, by: str = 'total_return_pct', ascending: bool = False) -> pd.DataFrame:
        return self.table.sort_values(by, ascending=ascending).reset_index(drop=True)


def compare_strategies(strategies: Optional[Dict[str, SignalFunc]] = None, ticker: str = "AAPL",
                        start_date=None, end_date=None, initial_capital: float = 10_000,
                        risk_per_trade: float = 2.0, stop_loss_pct: Optional[float] = 5.0,
                        take_profit_pct: Optional[float] = 10.0,
                        fractional_shares: bool = False) -> StrategyComparison:
    """
    Run every strategy on the same ticker and window, side by side.

    Args:
        strategies: name -> signal function; defaults to backtester.STRATEGIES
        ticker, start_date, end_date: the shared test window (defaults to 1 year to today)
        initial_capital, risk_per_trade, stop_loss_pct, take_profit_pct: shared engine settings
        fractional_shares: pass True for higher-priced assets (e.g. BTC-USD) —
            whole-share sizing can round every trade down to 0 shares when the
            risk budget is smaller than one share's stop distance, which
            silently produces "0 trades" indistinguishable from "no signal"
            (see BacktestResult.metrics['skipped_zero_size'])

    Returns:
        StrategyComparison with a ranked table and each strategy's full BacktestResult
    """
    strategies = strategies or STRATEGIES
    end_date = pd.Timestamp(end_date) if end_date else pd.Timestamp(datetime.now().date())
    start_date = pd.Timestamp(start_date) if start_date else end_date - timedelta(days=365)
    engine_kwargs = dict(initial_capital=initial_capital, risk_per_trade=risk_per_trade,
                         stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                         fractional_shares=fractional_shares)

    print(f"Comparing {len(strategies)} strategies on {ticker} "
          f"({start_date.date()} → {end_date.date()})...")
    rows, results = [], {}
    for name, fn in strategies.items():
        result = _run_one(fn, name, ticker, start_date, end_date, engine_kwargs)
        results[name] = result
        rows.append(_metrics_row(result, strategy=name, ticker=ticker))

    table = pd.DataFrame(rows).sort_values('total_return_pct', ascending=False).reset_index(drop=True)
    return StrategyComparison(ticker=ticker, start_date=start_date, end_date=end_date,
                               table=table, results=results)


# ============================================================================
# 2. Parameter sweep (grid search)
# ============================================================================

@dataclass
class SweepResult:
    strategy_name: str
    ticker: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    param_names: List[str]
    table: pd.DataFrame
    results: Dict[Tuple, BacktestResult] = field(default_factory=dict)

    def best(self, rank_by: str = 'sharpe_ratio', min_trades: int = 5) -> Optional[dict]:
        """
        Top combination by rank_by, restricted to combos with at least
        min_trades closed trades — otherwise "best" is whichever fluke had
        one lucky trade.
        """
        eligible = self.table[self.table['closed_trades'] >= min_trades]
        if eligible.empty:
            return None
        row = eligible.sort_values(rank_by, ascending=False).iloc[0]
        return {p: row[p] for p in self.param_names}


def parameter_sweep(strategy_builder: Callable[..., SignalFunc], param_grid: Dict[str, Sequence],
                     ticker: str = "AAPL", start_date=None, end_date=None,
                     strategy_name: Optional[str] = None,
                     valid_combo: Optional[Callable[[dict], bool]] = None,
                     warmup_days: int = DEFAULT_WARMUP_DAYS, initial_capital: float = 10_000,
                     risk_per_trade: float = 2.0, stop_loss_pct: Optional[float] = 5.0,
                     take_profit_pct: Optional[float] = 10.0,
                     fractional_shares: bool = False) -> SweepResult:
    """
    Grid search a strategy's parameters on one ticker and window.

    Args:
        strategy_builder: a function like make_sma_crossover(fast, slow) that
            returns a signal function for a given set of parameters
        param_grid: {param_name: [values to try]} — every combination is tested
        valid_combo: optional filter, e.g. `lambda p: p['fast'] < p['slow']`,
            to skip combinations that don't make sense
        warmup_days: raise this if the grid includes long periods (e.g. an SMA
            slower than ~280, given the 400-day default)
        fractional_shares: set True for higher-priced tickers (e.g. BTC-USD) —
            see compare_strategies()'s docstring for why whole-share sizing can
            silently zero out every trade

    Returns:
        SweepResult with one row per combination and `.best()` for the top pick
    """
    end_date = pd.Timestamp(end_date) if end_date else pd.Timestamp(datetime.now().date())
    start_date = pd.Timestamp(start_date) if start_date else end_date - timedelta(days=365)
    engine_kwargs = dict(initial_capital=initial_capital, risk_per_trade=risk_per_trade,
                         stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                         fractional_shares=fractional_shares)
    name = strategy_name or getattr(strategy_builder, '__name__', 'strategy')

    param_names = list(param_grid.keys())
    combos = [dict(zip(param_names, values)) for values in itertools.product(*param_grid.values())]
    if valid_combo:
        combos = [c for c in combos if valid_combo(c)]
    if not combos:
        raise ValueError("param_grid (after valid_combo filtering) produced no combinations to test")

    print(f"Sweeping {len(combos)} combinations of {name} on {ticker} "
          f"({start_date.date()} → {end_date.date()})...")
    rows, results = [], {}
    for combo in combos:
        fn = strategy_builder(**combo)
        result = _run_one(fn, name, ticker, start_date, end_date, engine_kwargs, warmup_days)
        key = tuple(combo[p] for p in param_names)
        results[key] = result
        rows.append(_metrics_row(result, ticker=ticker, **combo))

    table = pd.DataFrame(rows)
    return SweepResult(strategy_name=name, ticker=ticker, start_date=start_date, end_date=end_date,
                        param_names=param_names, table=table, results=results)


# ============================================================================
# 3. Asset + timeframe tester
# ============================================================================

@dataclass
class MatrixResult:
    table: pd.DataFrame   # long form: strategy, ticker, years, metrics...
    results: Dict[Tuple[str, str, float], BacktestResult] = field(default_factory=dict)

    def pivot(self, metric: str = 'total_return_pct', years: Optional[float] = None) -> pd.DataFrame:
        """Strategy × ticker grid of one metric, optionally filtered to one timeframe"""
        df = self.table if years is None else self.table[self.table['years'] == years]
        return df.pivot(index='strategy', columns='ticker', values=metric)

    def best_per_strategy(self, metric: str = 'sharpe_ratio') -> pd.DataFrame:
        """Which asset (and timeframe) each strategy did best on"""
        idx = self.table.groupby('strategy')[metric].idxmax()
        cols = ['strategy', 'ticker', 'years', metric, 'total_return_pct',
                'win_rate_pct', 'closed_trades', 'has_edge']
        return self.table.loc[idx, cols].sort_values(metric, ascending=False).reset_index(drop=True)


def multi_asset_test(strategies: Optional[Dict[str, SignalFunc]] = None,
                      tickers: Sequence[str] = ("AAPL", "BTC-USD", "SPY"),
                      years: Union[float, Sequence[float]] = 3, end_date=None,
                      initial_capital: float = 10_000, risk_per_trade: float = 2.0,
                      stop_loss_pct: Optional[float] = 5.0,
                      take_profit_pct: Optional[float] = 10.0,
                      fractional_shares: bool = True) -> MatrixResult:
    """
    Run every strategy on every ticker (optionally over several timeframes).

    Args:
        strategies: name -> signal function; defaults to backtester.STRATEGIES
        tickers: assets to test
        years: a single lookback in years, or a list to sweep timeframes too
            (e.g. [1, 2, 3])
        fractional_shares: defaults True here (unlike compare_strategies)
            because the default ticker list includes BTC-USD — at whole-share
            sizing, $10k capital / 2% risk / 5% stop can't afford 1 whole BTC
            above roughly $4k, so every BTC-USD backtest would silently
            produce 0 trades on every strategy. Check
            `MatrixResult.table['skipped_zero_size']` if you turn this off.

    Returns:
        MatrixResult — a long table plus `.pivot()` for heatmaps and
        `.best_per_strategy()` for "which asset does this strategy actually work on"
    """
    strategies = strategies or STRATEGIES
    years_list = [years] if isinstance(years, (int, float)) else list(years)
    end_date = pd.Timestamp(end_date) if end_date else pd.Timestamp(datetime.now().date())
    engine_kwargs = dict(initial_capital=initial_capital, risk_per_trade=risk_per_trade,
                         stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                         fractional_shares=fractional_shares)

    total = len(strategies) * len(tickers) * len(years_list)
    print(f"Running {total} backtests: {len(strategies)} strategies × "
          f"{len(tickers)} assets × {len(years_list)} timeframe(s)...")

    rows, results, done = [], {}, 0
    for yrs in years_list:
        start_date = end_date - timedelta(days=int(365 * yrs))
        for ticker in tickers:
            for name, fn in strategies.items():
                done += 1
                try:
                    result = _run_one(fn, name, ticker, start_date, end_date, engine_kwargs)
                except ValueError as e:
                    print(f"  [{done}/{total}] {name} on {ticker} ({yrs:g}y): skipped — {e}")
                    continue
                results[(name, ticker, yrs)] = result
                rows.append(_metrics_row(result, strategy=name, ticker=ticker, years=yrs))

    if not rows:
        raise ValueError("No successful backtests — check the ticker list and date range")

    table = pd.DataFrame(rows)
    return MatrixResult(table=table, results=results)


# ============================================================================
# 4. Signal combiner (AND / OR)
# ============================================================================

def combine_signals(signals: Sequence[SignalFunc], mode: str = 'AND',
                     buy_mode: Optional[str] = None, sell_mode: Optional[str] = None,
                     name: Optional[str] = None) -> SignalFunc:
    """
    Merge several signal functions into one that requires (or accepts) agreement.

    Args:
        signals: two or more (df, i) -> "buy"|"sell"|"hold" functions
        mode: 'AND' — every signal must agree before acting (fewer, stronger
              trades). 'OR' — any one signal is enough (more trades, weaker filter).
        buy_mode / sell_mode: override the two sides independently. The
              recommended combo — buy_mode='AND', sell_mode='OR' — requires
              agreement to get in but exits on the first warning; pass those
              explicitly if you want that instead of a uniform `mode`.
        name: label for reports; defaults to a name built from the inputs

    If both sides trigger on the same bar (only possible with OR), sell wins —
    risk-off breaks the tie.
    """
    buy_mode = (buy_mode or mode).upper()
    sell_mode = (sell_mode or mode).upper()
    if buy_mode not in ('AND', 'OR') or sell_mode not in ('AND', 'OR'):
        raise ValueError("mode/buy_mode/sell_mode must be 'AND' or 'OR'")
    n = len(signals)
    if n < 2:
        raise ValueError("combine_signals needs at least 2 signals")

    def combined(df: pd.DataFrame, i: int) -> str:
        votes = [s(df, i) for s in signals]
        buys, sells = votes.count('buy'), votes.count('sell')
        buy_trigger = (buys == n) if buy_mode == 'AND' else (buys > 0)
        sell_trigger = (sells == n) if sell_mode == 'AND' else (sells > 0)
        if sell_trigger:
            return 'sell'
        if buy_trigger:
            return 'buy'
        return 'hold'

    labels = [getattr(s, '__name__', f'signal{i}') for i, s in enumerate(signals)]
    combined.__name__ = name or f"{buy_mode.lower()}buy_{sell_mode.lower()}sell({'+'.join(labels)})"
    return combined


# ============================================================================
# 5. Report generator
# ============================================================================

_REPORT_CSS = """
<style>
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background:#0d0d0d; color:#e8e8e5; margin:0; padding:32px 40px 64px; }
  h1 { font-size:1.7rem; margin-bottom:4px; }
  h2 { font-size:1.25rem; margin-top:52px; border-bottom:1px solid #2c2c2a; padding-bottom:8px; }
  p.meta { color:#898781; font-size:0.85rem; margin:4px 0 20px; }
  table { border-collapse:collapse; width:100%; margin:16px 0 32px; font-size:0.86rem; }
  th, td { padding:7px 12px; text-align:right; border-bottom:1px solid #2c2c2a; white-space:nowrap; }
  th:first-child, td:first-child { text-align:left; }
  th { color:#c3c2b7; font-weight:600; background:#1a1a19; position:sticky; top:0; }
  tr.edge td:first-child::before { content:"✓ "; color:#0ca30c; font-weight:700; }
  tr.edge { background: rgba(12,163,12,0.08); }
  .table-wrap { overflow-x:auto; }
  .callout { background:#1a1a19; border:1px solid #2c2c2a; border-radius:8px;
             padding:16px 20px; margin:16px 0 32px; font-size:0.9rem; line-height:1.55; }
  .callout b { color:#ffffff; }
  .disclaimer { color:#898781; font-size:0.8rem; margin-top:64px;
                border-top:1px solid #2c2c2a; padding-top:16px; line-height:1.6; }
  .chart { margin:16px 0 32px; }
</style>
"""


def _table_html(df: pd.DataFrame, edge_mask: Optional[pd.Series] = None) -> str:
    """Render a DataFrame as a styled HTML table, checkmarking rows that clear the edge bar"""
    df = df.copy()
    if edge_mask is None and 'has_edge' in df.columns:
        edge_mask = df['has_edge']
    if 'has_edge' in df.columns:
        df = df.drop(columns=['has_edge'])
    for col in df.select_dtypes(include='number').columns:
        df[col] = df[col].round(2)

    header = ''.join(f"<th>{str(c).replace('_', ' ').title()}</th>" for c in df.columns)
    body_rows = []
    for pos, (idx, row) in enumerate(df.iterrows()):
        is_edge = bool(edge_mask.iloc[pos]) if edge_mask is not None else False
        cells = ''.join(f"<td>{'–' if pd.isna(v) else v}</td>" for v in row)
        row_class = ' class="edge"' if is_edge else ''
        body_rows.append(f"<tr{row_class}>{cells}</tr>")

    return (f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table></div>')


def generate_report(comparison: Optional[StrategyComparison] = None,
                     sweeps: Optional[List[SweepResult]] = None,
                     matrix: Optional[MatrixResult] = None,
                     output_path: str = "reports/strategy_lab.html",
                     edge_kwargs: Optional[dict] = None) -> str:
    """
    Write a self-contained HTML report from whichever analyses were run.

    Args:
        comparison: result of compare_strategies()
        sweeps: list of parameter_sweep() results
        matrix: result of multi_asset_test()
        output_path: where to write the file (parent directories are created)
        edge_kwargs: override meets_edge_criteria()'s thresholds for the
            "Strategies With a Statistical Edge" section (defaults to the
            standard 50 trades / 45% win rate / positive expectancy bar)

    Returns:
        Absolute path to the written file
    """
    crit = {'min_trades': 50, 'min_win_rate': 45.0, 'min_expectancy': 0.0, **(edge_kwargs or {})}
    sections: List[str] = []
    edge_frames: List[pd.DataFrame] = []

    if comparison is not None:
        chart = ranking_bar_chart(comparison.table, 'total_return_pct',
                                   title=f"{comparison.ticker} — Total Return by Strategy")
        mask = _edge_mask(comparison.table, edge_kwargs)
        edge_frames.append(comparison.table[mask].assign(source=f"compare · {comparison.ticker}"))
        sections.append(f"""
        <h2>Strategy Comparison — {comparison.ticker}</h2>
        <p class="meta">{comparison.start_date.date()} → {comparison.end_date.date()}</p>
        <div class="chart">{chart.to_html(full_html=False, include_plotlyjs=False)}</div>
        {_table_html(comparison.table, mask)}
        """)

    for sweep in (sweeps or []):
        best = sweep.best()
        best_html = (f"<b>Best by Sharpe (min 5 trades):</b> " +
                     ", ".join(f"{k}={v}" for k, v in best.items())) if best else \
                    "No combination cleared even the 5-trade sanity floor — widen the window or the grid."
        mask = _edge_mask(sweep.table, edge_kwargs)
        edge_frames.append(sweep.table[mask].assign(
            strategy=sweep.strategy_name, source=f"sweep · {sweep.ticker}"))
        sections.append(f"""
        <h2>Parameter Sweep — {sweep.strategy_name} on {sweep.ticker}</h2>
        <p class="meta">{len(sweep.table)} combinations ·
        {sweep.start_date.date()} → {sweep.end_date.date()}</p>
        <div class="callout">{best_html}</div>
        {_table_html(sweep.table.sort_values('sharpe_ratio', ascending=False), mask)}
        """)

    if matrix is not None:
        chart_html = []
        for metric, label in [('total_return_pct', 'Total Return (%)'), ('sharpe_ratio', 'Sharpe Ratio')]:
            for yrs in sorted(matrix.table['years'].unique()):
                pivot = matrix.pivot(metric, years=yrs)
                fig = heatmap_figure(pivot, metric_label=label, title=f"{label} — {yrs:g}y window")
                chart_html.append(f'<div class="chart">{fig.to_html(full_html=False, include_plotlyjs=False)}</div>')

        mask = _edge_mask(matrix.table, edge_kwargs)
        edge_frames.append(matrix.table[mask].assign(source='asset × timeframe matrix'))
        best_df = matrix.best_per_strategy('sharpe_ratio')

        pooled = pooled_edge_table(matrix, **crit)
        pooled_mask = _edge_mask(pooled, edge_kwargs)
        edge_frames.append(pooled[pooled_mask].assign(
            ticker=pooled[pooled_mask]['sources'].astype(str) + ' assets pooled',
            source='pooled across assets') if pooled_mask.any() else pooled.iloc[0:0])

        sections.append(f"""
        <h2>Asset × Timeframe Matrix</h2>
        <p class="meta">{matrix.table['strategy'].nunique()} strategies ×
        {matrix.table['ticker'].nunique()} assets ×
        {matrix.table['years'].nunique()} timeframe(s)</p>
        {''.join(chart_html)}
        <p class="meta">Best asset/timeframe per strategy (by Sharpe):</p>
        {_table_html(best_df, best_df['has_edge'])}
        <p class="meta">Full matrix:</p>
        {_table_html(matrix.table, mask)}

        <h3>Pooled Across Assets</h3>
        <p class="meta">Each strategy's closed trades pooled across every asset/timeframe
        tested above — a way to reach a meaningful sample when no single asset alone
        produces 50+ trades. See <code>pool_trades()</code>'s docstring for the caveat
        on correlated assets.</p>
        {_table_html(pooled, pooled_mask)}
        """)

    if edge_frames:
        edge_df = pd.concat(edge_frames, ignore_index=True, sort=False)
    else:
        edge_df = pd.DataFrame()

    if edge_df.empty:
        edge_section = f"""
        <div class="callout"><b>Nothing tested here cleared the bar</b>
        (≥{crit['min_trades']} closed trades, ≥{crit['min_win_rate']:g}% win rate,
        positive expectancy). That is itself a real result, not a bug — a slow
        crossover strategy on a few years of daily bars for one asset typically
        produces well under 50 trades, so the win rate isn't trustworthy yet
        either way. Widen the search before concluding nothing works: more
        assets, more history, a faster-firing strategy, or combine several
        assets' trades into one sample.</div>
        """
    else:
        edge_section = _table_html(edge_df.drop(columns=['has_edge'], errors='ignore'))

    sections.append(f"<h2>Strategies With a Statistical Edge</h2>{edge_section}")

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Strategy Lab Report</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
{_REPORT_CSS}</head><body>
<h1>📊 Strategy Laboratory Report</h1>
<p class="meta">Generated {datetime.now():%Y-%m-%d %H:%M} · no commissions or slippage modeled</p>
{''.join(sections)}
<div class="disclaimer">
<b>Edge criteria:</b> ≥{crit['min_trades']} closed trades, win rate ≥ {crit['min_win_rate']:g}%,
positive expectancy per trade — all three, not any one.<br>
<b>What this report is not:</b> a recommendation. Every result here comes from
historical data the strategy (or its parameters) may have been implicitly
fitted to. Treat a passing row as "worth testing out-of-sample," not "ready to
trade" — see the module docstring in <code>strategy_lab.py</code> for the full
caveat. No commissions, slippage, or borrow costs are modeled.
</div>
</body></html>"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f"\nReport written to {out.resolve()}")
    return str(out.resolve())


# ============================================================================
# Demo
# ============================================================================

def main():
    from backtester import make_sma_crossover, make_rsi_reversion, sma_crossover, rsi_reversion

    print("=" * 70)
    print("PHASE 3: STRATEGY LABORATORY")
    print("=" * 70)

    # 1. Compare every built-in strategy on AAPL
    print("\n--- 1. Strategy Comparison (AAPL, 3y) ---")
    comparison = compare_strategies(ticker="AAPL", start_date=pd.Timestamp(datetime.now().date()) - timedelta(days=365 * 3))
    print(comparison.ranked()[['strategy', 'total_return_pct', 'win_rate_pct', 'sharpe_ratio',
                                'max_drawdown_pct', 'closed_trades', 'has_edge']].to_string(index=False))

    # 2. Sweep SMA crossover periods
    print("\n--- 2. Parameter Sweep (SMA crossover, AAPL, 3y) ---")
    sweep = parameter_sweep(
        make_sma_crossover,
        param_grid={'fast': [10, 20, 30], 'slow': [50, 100, 150]},
        ticker="AAPL",
        start_date=pd.Timestamp(datetime.now().date()) - timedelta(days=365 * 3),
        valid_combo=lambda p: p['fast'] < p['slow'],
    )
    print(sweep.table.sort_values('sharpe_ratio', ascending=False)
          [['fast', 'slow', 'total_return_pct', 'sharpe_ratio', 'closed_trades']].to_string(index=False))
    best = sweep.best()
    print(f"Best (min 5 trades): {best}")

    # 3. Multi-asset matrix
    print("\n--- 3. Asset × Timeframe Matrix (AAPL, BTC-USD, SPY — 3y) ---")
    matrix = multi_asset_test(tickers=("AAPL", "BTC-USD", "SPY"), years=3)
    print("\nBest asset per strategy (by Sharpe):")
    print(matrix.best_per_strategy('sharpe_ratio').to_string(index=False))
    print("\nPooled across all 3 assets (the honest way to reach n=50+ when no "
          "single asset gets there alone):")
    pooled = pooled_edge_table(matrix)
    print(pooled.to_string(index=False))

    # 4. Signal combiner: MACD + RSI, both AND (stricter) and OR (looser)
    print("\n--- 4. Signal Combiner (MACD + RSI) ---")
    from backtester import macd_crossover
    and_combo = combine_signals([macd_crossover, rsi_reversion], buy_mode='AND', sell_mode='OR',
                                name='Combined (AND buy / OR sell)')
    or_combo = combine_signals([macd_crossover, rsi_reversion], mode='OR',
                               name='Combined (OR / OR)')
    combo_comparison = compare_strategies(
        strategies={'MACD Crossover': macd_crossover, 'RSI Mean Reversion': rsi_reversion,
                    'Combined (AND buy / OR sell)': and_combo, 'Combined (OR / OR)': or_combo},
        ticker="AAPL",
        start_date=pd.Timestamp(datetime.now().date()) - timedelta(days=365 * 3),
    )
    print(combo_comparison.ranked()[['strategy', 'total_return_pct', 'win_rate_pct',
                                      'sharpe_ratio', 'closed_trades']].to_string(index=False))
    print("(AND requires both signals on the exact same bar — strict by design; "
          "it can validly produce zero trades, which is itself a finding.)")

    # 5. Report
    print("\n--- 5. Report ---")
    generate_report(comparison=comparison, sweeps=[sweep], matrix=matrix,
                    output_path="reports/strategy_lab.html")

    print("\n💡 Open reports/strategy_lab.html in a browser for the full write-up.\n")


if __name__ == "__main__":
    main()
