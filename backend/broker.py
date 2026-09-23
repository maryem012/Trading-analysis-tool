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

import os
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = True

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
