"""
Plain-language reasoning behind a strategy's current signal.

The strategy functions in backtester.py only return non-'hold' on the exact
bar a cross/threshold event happens — they don't track how long a trend has
been in place. Each explainer here re-derives that by scanning backward from
bar i, so the text can say "since 3 days ago" rather than just restating the
signal itself.
"""

from __future__ import annotations

import pandas as pd


def _bars_since_state_change(series_a: pd.Series, series_b: pd.Series, i: int, above_now: bool) -> int:
    """How many consecutive prior bars share today's a-vs-b relationship."""
    n, j = 0, i
    while j > 0:
        a_prev, b_prev = series_a.iloc[j - 1], series_b.iloc[j - 1]
        if pd.isna(a_prev) or pd.isna(b_prev) or (a_prev > b_prev) != above_now:
            break
        n, j = n + 1, j - 1
    return n


def _since_phrase(n: int) -> str:
    if n == 0:
        return "today"
    return "1 day ago" if n == 1 else f"{n} days ago"


def _explain_crossover(df: pd.DataFrame, i: int, fast_col: str, slow_col: str,
                        fast_label: str, slow_label: str) -> str:
    fast, slow = df[fast_col], df[slow_col]
    if i < 1 or pd.isna(fast.iloc[i]) or pd.isna(slow.iloc[i]):
        return f"Not enough data yet to compare the {fast_label} and {slow_label} averages."

    above_now = fast.iloc[i] > slow.iloc[i]
    n = _bars_since_state_change(fast, slow, i, above_now)
    trend = "above" if above_now else "below"

    if n == 0:
        verb = "crossed above" if above_now else "crossed below"
        return f"{fast_label} just {verb} {slow_label} today."
    return f"{fast_label} has been {trend} {slow_label} since {_since_phrase(n)}."


def _explain_sma_crossover(df: pd.DataFrame, i: int) -> str:
    return _explain_crossover(df, i, "sma_20", "sma_50", "the 20-day average", "the 50-day average")


def _explain_sma_50_200_crossover(df: pd.DataFrame, i: int) -> str:
    return _explain_crossover(df, i, "sma_50", "sma_200", "the 50-day average", "the 200-day average")


def _explain_macd_crossover(df: pd.DataFrame, i: int) -> str:
    return _explain_crossover(df, i, "macd", "macd_signal", "the MACD line", "its signal line")


def _explain_rsi_reversion(df: pd.DataFrame, i: int, oversold: float = 30, overbought: float = 70) -> str:
    rsi = df["rsi"].iloc[i] if i < len(df) else None
    if rsi is None or pd.isna(rsi):
        return "RSI isn't available yet — not enough bars of data."
    if rsi <= oversold:
        return f"RSI is {rsi:.0f} — oversold territory (≤ {oversold:g}), often read as a bounce setup."
    if rsi >= overbought:
        return f"RSI is {rsi:.0f} — overbought territory (≥ {overbought:g}), often read as due for a pullback."
    return f"RSI is {rsi:.0f} — neutral range ({oversold:g}–{overbought:g}), no reversion signal right now."


def _explain_bollinger_reversion(df: pd.DataFrame, i: int) -> str:
    close, lower, upper = df["close"], df["bb_lower"], df["bb_upper"]
    if i < 1 or pd.isna(close.iloc[i]) or pd.isna(lower.iloc[i]) or pd.isna(upper.iloc[i]):
        return "Not enough data yet to compare price against the Bollinger Bands."

    c, lo, up = close.iloc[i], lower.iloc[i], upper.iloc[i]
    if c <= lo:
        return f"Price (${c:.2f}) is at or below the lower band (${lo:.2f}) — stretched to the downside."
    if c >= up:
        return f"Price (${c:.2f}) is at or above the upper band (${up:.2f}) — stretched to the upside."
    mid = (lo + up) / 2
    side = "upper" if c > mid else "lower"
    return f"Price (${c:.2f}) is inside the bands, drifting toward the {side} side — no bounce/fade signal right now."


_EXPLAINERS = {
    "sma_crossover": _explain_sma_crossover,
    "sma_50_200_crossover": _explain_sma_50_200_crossover,
    "rsi_reversion": _explain_rsi_reversion,
    "macd_crossover": _explain_macd_crossover,
    "bollinger_reversion": _explain_bollinger_reversion,
}


def explain_signal(strategy_id: str, df: pd.DataFrame, i: int) -> str:
    """Plain-language reasoning for what strategy_id's signal is doing at bar i."""
    fn = _EXPLAINERS.get(strategy_id)
    if fn is None:
        return ""
    try:
        text = fn(df, i)
    except Exception:
        return ""
    return text[:1].upper() + text[1:] if text else text
