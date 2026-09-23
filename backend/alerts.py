"""
Push notification alerts.

A browser subscribes to a watchlist of (ticker, strategy_id) pairs. A
background loop, started from api.py's startup event, re-checks each pair on
an interval and sends a Web Push notification the moment a signal changes
away from "hold" — not on every check, so a standing signal doesn't re-notify
every interval.

Storage is two local JSON files under backend/data/ — this is a personal,
single-process app, not a multi-tenant service, so a database is overkill.
Not safe for high-concurrency writes; fine for one browser subscribing
occasionally.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

from pywebpush import WebPushException, webpush

from signal_check import current_signal as _current_signal
from storage import DATA_DIR, load_json as _load_json, save_json as _save_json

logger = logging.getLogger("alerts")

SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
LAST_SIGNALS_FILE = DATA_DIR / "last_signals.json"

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:you@example.com")
CHECK_INTERVAL_MINUTES = float(os.environ.get("ALERT_CHECK_INTERVAL_MINUTES", "15"))


# ---------------------------------------------------------------- subscriptions

def save_subscription(subscription: dict, watchlist: List[dict]) -> None:
    """
    subscription: the raw PushSubscription JSON the browser's PushManager
        returns — {"endpoint": ..., "keys": {"p256dh": ..., "auth": ...}}
    watchlist: [{"ticker": "AAPL", "strategy_id": "sma_crossover"}, ...]
    """
    endpoint = subscription["endpoint"]
    subs = _load_json(SUBSCRIPTIONS_FILE, {})
    subs[endpoint] = {"subscription": subscription, "watchlist": watchlist}
    _save_json(SUBSCRIPTIONS_FILE, subs)


def remove_subscription(endpoint: str) -> None:
    subs = _load_json(SUBSCRIPTIONS_FILE, {})
    subs.pop(endpoint, None)
    _save_json(SUBSCRIPTIONS_FILE, subs)


def get_subscription(endpoint: str) -> Optional[dict]:
    return _load_json(SUBSCRIPTIONS_FILE, {}).get(endpoint)


def list_subscriptions() -> Dict[str, dict]:
    return _load_json(SUBSCRIPTIONS_FILE, {})


# --------------------------------------------------------------------- sending

def send_push(subscription: dict, title: str, body: str, url: str = "/") -> bool:
    """
    Send one Web Push message. Returns False if it couldn't be sent — and
    drops the subscription if the push service says it's gone (the user
    uninstalled the PWA, cleared site data, etc.).
    """
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY not set — can't send push notifications")
        return False
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_SUBJECT},
        )
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):  # subscription expired or was revoked
            remove_subscription(subscription.get("endpoint", ""))
        logger.warning(f"Push failed ({status}): {e}")
        return False


def check_and_notify(strategies: Dict[str, tuple]) -> int:
    """
    Re-check every (ticker, strategy) pair anyone is subscribed to and push a
    notification for each one whose signal just changed to buy/sell.

    strategies: the same {id: (name, fn)} dict api.py builds from backtester.py

    Returns the number of notifications actually sent (for logging/tests).
    """
    subs = list_subscriptions()
    if not subs:
        return 0

    last_signals = _load_json(LAST_SIGNALS_FILE, {})
    sent = 0
    signal_cache: Dict[Tuple[str, str], Optional[str]] = {}

    for endpoint, entry in list(subs.items()):
        for item in entry.get("watchlist", []):
            ticker, sid = item.get("ticker"), item.get("strategy_id")
            if not ticker or sid not in strategies:
                continue
            key = (ticker, sid)
            if key not in signal_cache:
                _, fn = strategies[sid]
                signal_cache[key] = _current_signal(ticker, fn)
            signal = signal_cache[key]
            if signal is None:
                continue

            state_key = f"{ticker}|{sid}"
            previous = last_signals.get(state_key)
            last_signals[state_key] = signal

            if signal in ("buy", "sell") and signal != previous:
                name = strategies[sid][0]
                title = f"{'🟢 BUY' if signal == 'buy' else '🔴 SELL'} signal — {ticker}"
                body = f"{name} just triggered a {signal.upper()} on {ticker}."
                if send_push(entry["subscription"], title, body):
                    sent += 1

    _save_json(LAST_SIGNALS_FILE, last_signals)
    return sent


# ------------------------------------------------------------------ scheduler

async def run_scheduler(strategies: Dict[str, tuple]) -> None:
    """Background loop — start once via asyncio.create_task() at app startup."""
    logger.info(f"Alert scheduler started — checking every {CHECK_INTERVAL_MINUTES} min")
    while True:
        try:
            sent = await asyncio.to_thread(check_and_notify, strategies)
            if sent:
                logger.info(f"Sent {sent} alert notification(s)")
        except Exception:
            logger.exception("Alert check failed")
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
