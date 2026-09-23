"""
Alpaca paper-trading integration.

Alpaca's own API is the system of record for cash, positions, and order
history — this module is a thin wrapper, not a local ledger. Nothing here
needs to survive a Railway redeploy because Alpaca remembers everything on
its own servers regardless of what happens to this container.

ALPACA_PAPER is hardcoded True for now (see the project plan) — flipping to
live trading later is meant to be a one-line change plus real (non-paper)
keys, not a rewrite.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

from signal_check import current_signal
from storage import DATA_DIR, load_json, save_json

logger = logging.getLogger("broker")

ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = True

# Auto-trade config is a separate, simpler concept from the push watchlist —
# no browser PushSubscription is involved, and a user might want one without
# the other. Kept in its own file rather than reusing alerts.py's storage.
AUTO_TRADE_FILE = DATA_DIR / "auto_trade.json"
AUTO_TRADE_LAST_SIGNALS_FILE = DATA_DIR / "auto_trade_last_signals.json"
MAX_AUTO_TRADE_ITEMS = 20

# Alpaca's notional (dollar-amount) orders only work for US equities/ETFs,
# not crypto — these are the crypto tickers this app otherwise supports.
_CRYPTO_SUFFIXES = ("-USD",)


def is_configured() -> bool:
    return bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)


def is_crypto(ticker: str) -> bool:
    return ticker.upper().endswith(_CRYPTO_SUFFIXES)


def _client() -> TradingClient:
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=ALPACA_PAPER)


def get_account() -> dict:
    a = _client().get_account()
    return {
        "status": str(a.status.value) if a.status else None,
        "cash": float(a.cash),
        "equity": float(a.equity),
        "buying_power": float(a.buying_power),
        "portfolio_value": float(a.portfolio_value),
    }


def list_positions() -> list[dict]:
    positions = _client().get_all_positions()
    return [
        {
            "ticker": p.symbol,
            "qty": float(p.qty),
            "avg_entry_price": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc) * 100,
        }
        for p in positions
    ]


def list_orders(limit: int = 50) -> list[dict]:
    orders = _client().get_orders(
        GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
    )
    return [
        {
            "id": str(o.id),
            "ticker": o.symbol,
            "side": str(o.side.value) if o.side else None,
            "qty": float(o.qty) if o.qty is not None else None,
            "notional": float(o.notional) if o.notional is not None else None,
            "status": str(o.status.value) if o.status else None,
            "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
            "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price is not None else None,
        }
        for o in orders
    ]


def place_market_order(ticker: str, side: str, notional: float) -> dict:
    if is_crypto(ticker):
        raise ValueError(f"{ticker} is a crypto asset — notional order placement isn't supported for it yet")

    order = MarketOrderRequest(
        symbol=ticker,
        notional=round(notional, 2),
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,  # required for notional/fractional orders
    )
    o = _client().submit_order(order)
    return {
        "id": str(o.id),
        "ticker": o.symbol,
        "side": str(o.side.value) if o.side else None,
        "notional": float(o.notional) if o.notional is not None else None,
        "status": str(o.status.value) if o.status else None,
        "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
    }


def close_position(ticker: str) -> Optional[dict]:
    try:
        o = _client().close_position(ticker)
    except Exception:
        return None
    return {
        "id": str(o.id),
        "ticker": o.symbol,
        "side": str(o.side.value) if o.side else None,
        "status": str(o.status.value) if o.status else None,
    }


# --------------------------------------------------------------- auto-trade

def get_auto_trade_items() -> List[dict]:
    return load_json(AUTO_TRADE_FILE, [])


def set_auto_trade_items(items: List[dict]) -> None:
    save_json(AUTO_TRADE_FILE, items)


def check_and_trade(strategies: Dict[str, tuple]) -> int:
    """
    Re-check every auto-trade pair and place a paper order the moment its
    signal flips to buy/sell — mirrors alerts.check_and_notify's flip
    detection, but acts on it instead of just notifying. Kept separate from
    alerts.py (push stays push-only) other than sharing signal_check.py.
    """
    items = get_auto_trade_items()
    if not items:
        return 0

    last_signals = load_json(AUTO_TRADE_LAST_SIGNALS_FILE, {})
    traded = 0

    for item in items:
        ticker, sid = item.get("ticker"), item.get("strategy_id")
        if not ticker or sid not in strategies or is_crypto(ticker):
            continue
        _, fn = strategies[sid]
        signal = current_signal(ticker, fn)
        if signal is None:
            continue

        state_key = f"{ticker}|{sid}"
        previous = last_signals.get(state_key)
        last_signals[state_key] = signal

        if signal not in ("buy", "sell") or signal == previous:
            continue

        try:
            if signal == "buy":
                place_market_order(ticker, "buy", float(item.get("notional", 50)))
            else:
                close_position(ticker)
            traded += 1
        except Exception:
            logger.exception(f"Auto-trade order failed for {ticker}/{sid}")

    save_json(AUTO_TRADE_LAST_SIGNALS_FILE, last_signals)
    return traded


async def run_scheduler(strategies: Dict[str, tuple]) -> None:
    """Background loop — start once via asyncio.create_task() at app startup."""
    from alerts import CHECK_INTERVAL_MINUTES  # deferred: avoids import ordering issues at module load

    logger.info(f"Auto-trade scheduler started — checking every {CHECK_INTERVAL_MINUTES} min")
    while True:
        try:
            traded = await asyncio.to_thread(check_and_trade, strategies)
            if traded:
                logger.info(f"Auto-trade placed {traded} order(s)")
        except Exception:
            logger.exception("Auto-trade check failed")
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
