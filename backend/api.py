"""
FastAPI backend — exposes backtester.py / strategy_lab.py / data_fetcher.py as
JSON endpoints for the web dashboard.

Run locally:
    cd backend
    uvicorn api:app --reload --port 8000

This file imports the repo-root modules directly rather than duplicating
logic — the sys.path insert below makes that work whether uvicorn is launched
from backend/ (as above) or from the repo root.
"""

from __future__ import annotations

import asyncio
import math
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Must run before importing alerts.py/broker.py — they read VAPID_*/ALERT_*/
# ALPACA_* env vars at module load time, so .env has to be loaded first or
# those come back empty.
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtester import (  # noqa: E402
    BacktestEngine, sma_crossover, make_sma_crossover, rsi_reversion,
    macd_crossover, bollinger_reversion,
)
from data_fetcher import DataFetcher  # noqa: E402
from strategy_lab import compare_strategies, multi_asset_test  # noqa: E402
import alerts  # noqa: E402
from explain import explain_signal  # noqa: E402
import broker  # noqa: E402

app = FastAPI(
    title="Trading Backtester API",
    description="Runs backtester.py / strategy_lab.py over yfinance data and returns JSON",
    version="1.1.0",
)

# CORS_ORIGINS is a comma-separated list; defaults to the local Next.js dev server
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# id -> (display name, signal function). The id is what the frontend sends back
# in request bodies; the name is what it shows in dropdowns and what
# strategy_lab's compare_strategies()/multi_asset_test() key their results by.
STRATEGIES = {
    "sma_crossover": ("SMA 20/50 Crossover", sma_crossover),
    "sma_50_200_crossover": ("SMA 50/200 Crossover", make_sma_crossover(50, 200)),
    "rsi_reversion": ("RSI Mean Reversion", rsi_reversion),
    "macd_crossover": ("MACD Crossover", macd_crossover),
    "bollinger_reversion": ("Bollinger Reversion", bollinger_reversion),
}
_NAME_TO_ID = {name: sid for sid, (name, _fn) in STRATEGIES.items()}


@app.on_event("startup")
async def _start_alert_scheduler():
    """
    Launch the background loop that checks every watched (ticker, strategy)
    pair on a timer and pushes a notification when a signal changes. A no-op
    if VAPID_PRIVATE_KEY isn't set — see alerts.py / generate_vapid.py.
    """
    asyncio.create_task(alerts.run_scheduler(STRATEGIES))


# A curated starting list for dropdowns/autocomplete — NOT a restriction.
# Every endpoint accepts any ticker yfinance recognizes (any stock, ETF, index
# prefixed "^", or crypto pair like "SOL-USD"); this is just what shows up
# before you type your own. Ordered for a small-account investor: diversified
# ETFs first (one share spreads risk across hundreds of companies, and the
# app's fractional-share sizing means even a $100 test isn't blocked by
# price), then well-known individual stocks, then indices, with crypto last
# since it's the most volatile and — per-coin price aside — the least
# beginner-friendly starting point.
ASSETS = [
    "SPY", "URTH", "^GSPC",  # S&P 500 ETF, MSCI World ETF, raw S&P 500 index — top picks
    "VTI", "QQQ", "DIA", "IWM",
    "AAPL", "MSFT", "GOOGL", "AMZN", "KO", "NVDA", "META", "TSLA", "NFLX", "AMD", "INTC",
    "^IXIC", "^DJI",
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD",
]


class BacktestRequest(BaseModel):
    ticker: str = Field(..., examples=["SPY"])
    strategy: str = Field(..., examples=["sma_crossover"])
    days: int = Field(365, ge=30, le=3650, description="Lookback window in calendar days")
    initial_capital: float = Field(10_000, gt=0)
    risk_per_trade: float = Field(2.0, gt=0, le=100)
    stop_loss_pct: Optional[float] = Field(5.0, gt=0)
    take_profit_pct: Optional[float] = Field(10.0, gt=0)
    # Whole-share sizing can silently round every trade to 0 shares once an
    # asset's price exceeds roughly (capital * risk% / stop%) — true by
    # default for a $10k account since BTC-USD is one of only 3 listed
    # assets and trades in the tens of thousands. See metrics.skipped_zero_size.
    fractional_shares: bool = Field(True)


class CompareRequest(BaseModel):
    ticker: str = Field(..., examples=["SPY"])
    days: int = Field(365, ge=30, le=3650)
    strategy_ids: Optional[List[str]] = Field(
        None, description="Subset of /api/strategies ids; omit to compare all of them")


class MatrixRequest(BaseModel):
    tickers: List[str] = Field(
        default_factory=lambda: ["SPY", "URTH", "^GSPC"], min_length=1, max_length=8,
        description="Up to 8 tickers — each new one is a fresh backtest per strategy, "
                    "so this scales fast (8 tickers × 5 strategies = 40 backtests)")
    years: float = Field(2.0, ge=0.5, le=10.0)
    strategy_ids: Optional[List[str]] = None


def _resolve_strategies(ids: Optional[List[str]]) -> dict:
    """ids -> {display name: signal fn}, as strategy_lab's functions expect"""
    ids = ids or list(STRATEGIES.keys())
    unknown = [i for i in ids if i not in STRATEGIES]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy id(s) {unknown}. See /api/strategies for valid ids.",
        )
    return {STRATEGIES[i][0]: STRATEGIES[i][1] for i in ids}


def _to_jsonable(obj):
    """
    Recursively convert a value tree (dicts/lists/DataFrame-derived scalars)
    into something Python's json module — and a browser's strict JSON.parse —
    can both handle.

    Three separate gotchas in one pass: (1) numpy scalar types (np.int64,
    np.bool_, np.float64) aren't natively JSON-serializable even though they
    look like plain numbers; (2) inf/-inf/NaN are valid Python floats but
    invalid JSON tokens; (3) pandas Timestamp/date objects need an explicit
    string format rather than whatever repr() gives them.
    """
    if obj is None:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, date):
        # covers datetime.date, datetime.datetime and pd.Timestamp — the
        # latter two both subclass date
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, pd.Series):
        return _to_jsonable(obj.to_dict())
    if pd.isna(obj) if np.isscalar(obj) else False:
        return None
    return obj


def _date_str(value) -> Optional[str]:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


@app.get("/")
def root():
    return {"status": "ok", "service": "trading-backtester-api"}


@app.get("/api/strategies")
def list_strategies():
    return [{"id": sid, "name": name} for sid, (name, _fn) in STRATEGIES.items()]


@app.get("/api/assets")
def list_assets():
    return ASSETS


@app.get("/api/price-history")
def price_history(ticker: str, days: int = 365):
    """OHLCV + indicators for charting — the same columns the Streamlit dashboard plots."""
    try:
        fetcher = DataFetcher(ticker)
        df = fetcher.fetch_data(days=days)
        if df is None or len(df) == 0:
            raise HTTPException(status_code=400, detail=f"No data returned for '{ticker}'")
        df = fetcher.add_indicators(df)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Couldn't fetch {ticker}: {e}")

    cols = ["open", "high", "low", "close", "volume", "sma_20", "sma_50", "sma_200",
            "bb_upper", "bb_lower", "rsi", "macd", "macd_signal"]
    bars = []
    for date, row in df[cols].iterrows():
        bar = {"date": date.strftime("%Y-%m-%d")}
        bar.update({c: row[c] for c in cols})
        bars.append(bar)

    return _to_jsonable({"ticker": ticker.upper(), "days": days, "bars": bars})


@app.get("/api/signals")
def signals(ticker: str, days: int = 365):
    """
    Current indicator snapshot plus what every built-in strategy would do
    *right now* — the "recommendation" panel. This looks at the same data a
    backtest would see on its last bar; it is not a live intraday quote.
    """
    try:
        fetcher = DataFetcher(ticker)
        df = fetcher.fetch_data(days=days)
        if df is None or len(df) == 0:
            raise HTTPException(status_code=400, detail=f"No data returned for '{ticker}'")
        df = fetcher.add_indicators(df)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Couldn't fetch {ticker}: {e}")

    if len(df) < 2:
        raise HTTPException(status_code=400, detail="Not enough bars to compute signals")

    latest = fetcher.get_latest_signals(df)
    i = len(df) - 1
    recommendations = []
    for sid, (name, fn) in STRATEGIES.items():
        try:
            sig = fn(df, i)
        except Exception:
            sig = "hold"
        reason = explain_signal(sid, df, i)
        recommendations.append({"strategy_id": sid, "strategy_name": name, "signal": sig, "reason": reason})

    return _to_jsonable({
        "ticker": ticker.upper(),
        "as_of": latest["timestamp"],
        "close": latest["close"],
        "rsi": latest["rsi"],
        "macd": latest["macd"],
        "macd_signal": latest["macd_signal"],
        "sma_20": latest["sma_20"],
        "sma_50": latest["sma_50"],
        "sma_200": latest["sma_200"],
        "rsi_overbought": latest["rsi_overbought"],
        "rsi_oversold": latest["rsi_oversold"],
        "macd_bullish": latest["macd_bullish"],
        "price_above_sma_50": latest["price_above_sma_50"],
        "recommendations": recommendations,
    })


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    if req.strategy not in STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{req.strategy}'. See /api/strategies for valid ids.",
        )

    name, fn = STRATEGIES[req.strategy]
    end = pd.Timestamp(datetime.now().date())
    start = end - timedelta(days=req.days)

    engine = BacktestEngine(
        ticker=req.ticker,
        start_date=start,
        end_date=end,
        initial_capital=req.initial_capital,
        risk_per_trade=req.risk_per_trade,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
        fractional_shares=req.fractional_shares,
    )
    try:
        engine.load_data()
        result = engine.run(fn, strategy_name=name)
    except ValueError as e:
        # Bad ticker, empty window, etc. — the caller's fault, not the server's
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {e}")

    metrics = _to_jsonable(result.metrics)

    trades = result.trades_frame().copy()
    numeric_cols = list(trades.select_dtypes(include="number").columns)
    # Build plain-Python-object columns explicitly rather than via .apply(),
    # which — on pandas' newer string/nullable dtypes — can silently turn a
    # returned None back into a float NaN (or pd.NA) once it re-infers the
    # column's dtype. An explicit object-dtype Series keeps exactly what the
    # function returned: a real None, not a NaN standing in for it.
    trades["entry_date"] = pd.Series(
        [_date_str(v) for v in trades["entry_date"]], index=trades.index, dtype=object)
    trades["exit_date"] = pd.Series(
        [_date_str(v) for v in trades["exit_date"]], index=trades.index, dtype=object)
    for col in numeric_cols:
        trades[col] = pd.Series(
            [_to_jsonable(float(v)) for v in trades[col]], index=trades.index, dtype=object)
    trades_records = trades.to_dict(orient="records")

    buy_hold = result.data["close"] / float(result.data["close"].iloc[0]) * result.initial_capital
    equity_curve = [
        {"date": d.strftime("%Y-%m-%d"), "equity": _to_jsonable(float(v))}
        for d, v in result.equity_curve.items()
    ]
    buy_hold_curve = [
        {"date": d.strftime("%Y-%m-%d"), "equity": _to_jsonable(float(v))}
        for d, v in buy_hold.items()
    ]

    return {
        "ticker": result.ticker,
        "strategy": name,
        "strategy_id": req.strategy,
        "days": req.days,
        "initial_capital": result.initial_capital,
        "metrics": metrics,
        "trades": trades_records,
        "equity_curve": equity_curve,
        "buy_hold_curve": buy_hold_curve,
    }


@app.post("/api/compare")
def run_compare(req: CompareRequest):
    """Every requested strategy, same ticker and window, ranked side by side."""
    strategies = _resolve_strategies(req.strategy_ids)
    end = pd.Timestamp(datetime.now().date())
    start = end - timedelta(days=req.days)

    try:
        comparison = compare_strategies(strategies=strategies, ticker=req.ticker,
                                        start_date=start, end_date=end,
                                        fractional_shares=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {e}")

    table = comparison.table.copy()
    table["strategy_id"] = table["strategy"].map(_NAME_TO_ID)

    return _to_jsonable({
        "ticker": comparison.ticker,
        "start_date": comparison.start_date,
        "end_date": comparison.end_date,
        "rows": table.to_dict(orient="records"),
    })


@app.post("/api/matrix")
def run_matrix(req: MatrixRequest):
    """
    Every requested strategy x every requested asset, one lookback window.

    Slower than the other endpoints — each new (ticker, window) pair is a
    fresh yfinance fetch the first time it's requested (cached to disk under
    .cache/ afterward via strategy_lab.get_price_data), and this fires one
    backtest per strategy-asset pair.
    """
    if not req.tickers:
        raise HTTPException(status_code=400, detail="tickers must not be empty")
    strategies = _resolve_strategies(req.strategy_ids)

    try:
        result = multi_asset_test(strategies=strategies, tickers=tuple(req.tickers),
                                  years=req.years, fractional_shares=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {e}")

    table = result.table.copy()
    table["strategy_id"] = table["strategy"].map(_NAME_TO_ID)

    return _to_jsonable({"rows": table.to_dict(orient="records")})


# ============================================================================
# Push notification alerts (see alerts.py)
# ============================================================================

class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionModel(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class WatchlistItem(BaseModel):
    ticker: str
    strategy_id: str


class SubscribeRequest(BaseModel):
    subscription: PushSubscriptionModel
    watchlist: List[WatchlistItem] = Field(default_factory=list, max_length=20)


class UnsubscribeRequest(BaseModel):
    endpoint: str


class WatchlistUpdateRequest(BaseModel):
    endpoint: str
    watchlist: List[WatchlistItem] = Field(max_length=20)


class TestPushRequest(BaseModel):
    subscription: PushSubscriptionModel


@app.get("/api/push/vapid-public-key")
def push_vapid_public_key():
    if not alerts.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=503,
            detail="Push alerts aren't configured on this server — run "
                   "generate_vapid.py and set VAPID_PRIVATE_KEY/VAPID_PUBLIC_KEY.",
        )
    return {"publicKey": alerts.VAPID_PUBLIC_KEY}


@app.post("/api/push/subscribe")
def push_subscribe(req: SubscribeRequest):
    unknown = [w.strategy_id for w in req.watchlist if w.strategy_id not in STRATEGIES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown strategy id(s): {unknown}")
    alerts.save_subscription(
        req.subscription.model_dump(),
        [w.model_dump() for w in req.watchlist],
    )
    return {"status": "subscribed", "watching": len(req.watchlist)}


@app.post("/api/push/unsubscribe")
def push_unsubscribe(req: UnsubscribeRequest):
    alerts.remove_subscription(req.endpoint)
    return {"status": "unsubscribed"}


@app.put("/api/push/watchlist")
def push_update_watchlist(req: WatchlistUpdateRequest):
    entry = alerts.get_subscription(req.endpoint)
    if entry is None:
        raise HTTPException(status_code=404, detail="No subscription for that endpoint")
    unknown = [w.strategy_id for w in req.watchlist if w.strategy_id not in STRATEGIES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown strategy id(s): {unknown}")
    alerts.save_subscription(entry["subscription"], [w.model_dump() for w in req.watchlist])
    return {"status": "updated", "watching": len(req.watchlist)}


@app.get("/api/push/status")
def push_status(endpoint: str):
    entry = alerts.get_subscription(endpoint)
    if entry is None:
        return {"subscribed": False, "watchlist": []}
    return {"subscribed": True, "watchlist": entry.get("watchlist", [])}


@app.post("/api/push/test")
def push_test(req: TestPushRequest):
    ok = alerts.send_push(
        req.subscription.model_dump(),
        title="🔔 Test alert",
        body="If you can see this, push notifications are working.",
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Push send failed — see server logs")
    return {"status": "sent"}


# ============================================================================
# Broker (Alpaca paper trading — see broker.py)
# ============================================================================

class PlaceOrderRequest(BaseModel):
    ticker: str = Field(..., examples=["SPY"])
    side: str = Field(..., pattern="^(buy|sell)$")
    notional: float = Field(..., gt=0, le=1000, description="Dollar amount to buy/sell")


def _require_broker() -> None:
    if not broker.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Broker isn't configured on this server — set ALPACA_API_KEY/ALPACA_SECRET_KEY.",
        )


@app.get("/api/broker/status")
def broker_status():
    return {"configured": broker.is_configured(), "paper": broker.ALPACA_PAPER}


@app.get("/api/broker/account")
def broker_account():
    _require_broker()
    try:
        return _to_jsonable(broker.get_account())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Couldn't reach Alpaca: {e}")


@app.get("/api/broker/positions")
def broker_positions():
    _require_broker()
    try:
        return _to_jsonable(broker.list_positions())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Couldn't reach Alpaca: {e}")


@app.get("/api/broker/orders")
def broker_orders(limit: int = 50):
    _require_broker()
    try:
        return _to_jsonable(broker.list_orders(limit=limit))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Couldn't reach Alpaca: {e}")


@app.post("/api/broker/orders")
def broker_place_order(req: PlaceOrderRequest):
    _require_broker()
    if broker.is_crypto(req.ticker):
        raise HTTPException(
            status_code=400,
            detail=f"{req.ticker} is a crypto asset — order placement isn't supported for it yet.",
        )
    try:
        return _to_jsonable(broker.place_market_order(req.ticker, req.side, req.notional))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Order failed: {e}")


@app.post("/api/broker/positions/{ticker}/close")
def broker_close_position(ticker: str):
    _require_broker()
    result = broker.close_position(ticker)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No open position for {ticker.upper()}")
    return _to_jsonable(result)
