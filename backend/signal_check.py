"""
What would a strategy do right now? Shared by alerts.py (push notifications)
and broker.py (auto-trade) — both need the exact same "current signal"
computation, just reacting to it differently.
"""

from __future__ import annotations

import logging
from typing import Optional

from data_fetcher import DataFetcher

logger = logging.getLogger("signal_check")


def current_signal(ticker: str, strategy_fn) -> Optional[str]:
    """Same logic as /api/signals — what would this strategy do right now?"""
    try:
        fetcher = DataFetcher(ticker)
        df = fetcher.fetch_data(days=365)
        if df is None or len(df) < 2:
            return None
        df = fetcher.add_indicators(df)
        return strategy_fn(df, len(df) - 1)
    except Exception:
        logger.exception(f"Signal check failed for {ticker}")
        return None
