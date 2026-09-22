# Trading Analysis Tool

A Python-based trading analysis and visualization tool to analyze technical indicators and learn trading strategies.

- **Phase 1** — fetch market data, calculate indicators, chart them
- **Phase 2** — backtest a strategy on that history and measure whether it actually worked
- **Phase 3** — compare/sweep/combine strategies across assets to find one with a real statistical edge
- **Phase 4** — the same backtester behind a web API and dashboard (FastAPI + Next.js)

## Quick Start (5 mins)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the dashboard (no database needed yet)
```bash
streamlit run dashboard.py
```

Visit `http://localhost:8501` in your browser.

### That's it! Start exploring:
- Change the ticker (AAPL, MSFT, BTC-USD, etc.)
- Adjust the time range
- See price, volume, RSI, MACD, moving averages

---

## Project Structure

```
trading_tool/
├── data_fetcher.py      # Download data & calculate indicators
├── dashboard.py         # Streamlit visualization + backtest viewer
├── backtester.py        # Phase 2: trade simulation, metrics, strategies
├── strategy_lab.py      # Phase 3: strategy comparison, sweeps, reports
├── plots.py             # Plotly figures for backtests + strategy lab
├── quick_analysis.py    # Terminal snapshot of current indicators
├── db_store.py          # PostgreSQL storage (optional)
├── requirements.txt     # Python dependencies (Phase 1-3, Streamlit dashboard)
├── backend/             # Phase 4: FastAPI wrapper around backtester.py
│   └── api.py
├── frontend/            # Phase 4: Next.js web dashboard
│   └── app/, components/, lib/
└── README.md            # This file
```

---

## Indicators Included

**Trend Indicators:**
- SMA (20, 50, 200) — Simple Moving Averages
- EMA (12, 26) — Exponential Moving Averages
- Bollinger Bands — Volatility bands around price

**Momentum Indicators:**
- RSI (14) — Overbought/Oversold detection
- MACD — Trend and momentum strength

**Volume:**
- Raw volume with color coding

---

## Next Steps: How to Extend This

### Phase 1B: Save data locally (CSV)
Uncomment in `data_fetcher.py`:
```python
df_with_indicators.to_csv(f"{ticker}_data.csv")
```

### Phase 5: Paper trading
Run signals against live market data (fake money first).

---

## Phase 2: Backtesting

Run the built-in demo — SMA crossover on one year of AAPL:

```bash
python backtester.py           # defaults to AAPL, 1 year
python backtester.py MSFT 2    # ticker, years
```

Or open the dashboard and use **Backtest Settings** in the sidebar: pick a
strategy, capital, risk per trade, stop-loss and take-profit, then hit
**Run Backtest** for the equity curve, marked-up price chart, metrics and trade log.

### In code

```python
from backtester import BacktestEngine, sma_crossover

engine = BacktestEngine(
    ticker="AAPL",
    start_date="2024-01-01",
    end_date="2025-01-01",
    initial_capital=10_000,
    risk_per_trade=2.0,     # % of equity risked between entry and stop
    stop_loss_pct=5.0,      # None to trade without a stop
    take_profit_pct=10.0,   # None to let signals do the exiting
)
result = engine.run(sma_crossover)

print(result.summary())          # metrics report
result.trades_frame()            # every trade as a DataFrame
result.equity_curve              # equity per bar, as a Series
result.metrics['sharpe_ratio']   # individual metrics
```

### Writing your own strategy

A strategy is just a function that looks at the data up to bar `i` and returns
`"buy"`, `"sell"` or `"hold"`. Every indicator column from `data_fetcher.py` is
available on the frame:

```python
def rsi_and_trend(df, i):
    if df['rsi'].iloc[i] < 30 and df['close'].iloc[i] > df['sma_200'].iloc[i]:
        return 'buy'
    if df['rsi'].iloc[i] > 70:
        return 'sell'
    return 'hold'

result = engine.run(rsi_and_trend)
```

Add it to the `STRATEGIES` dict in `backtester.py` to make it selectable in the
dashboard.

### Metrics reported

Total return, buy & hold comparison, win rate, profit factor, Sharpe ratio, max
drawdown, average trade duration, average win/loss, expectancy, best/worst trade.

### How the simulation works

- Long-only, one position at a time
- A signal on a bar's **close** fills at the **next** bar's open — no look-ahead
- Stop-loss and take-profit are checked against each bar's low/high; a bar that
  hits both is assumed to hit the stop first
- Position size comes from `risk_per_trade`: `shares = (equity × risk%) / stop distance`,
  capped by available cash
- A position still open at the end stays open — it is marked to market in the
  equity curve, but trade stats (win rate, profit factor) count closed trades only
- **No commissions or slippage**, so results are optimistic

---

## Phase 3: Strategy Laboratory

`strategy_lab.py` runs many backtests against each other instead of one at a
time, and writes an HTML report of what actually held up:

```bash
python strategy_lab.py    # compares strategies, sweeps SMA periods, tests
                           # AAPL/BTC-USD/SPY, writes reports/strategy_lab.html
```

- **`compare_strategies()`** — every strategy in `STRATEGIES`, same ticker and
  window, ranked side by side
- **`parameter_sweep()`** — grid search a strategy builder's parameters (e.g.
  SMA fast/slow periods) and pick the best by Sharpe, gated on a minimum trade count
- **`multi_asset_test()`** — every strategy × every asset × (optionally)
  several timeframes in one matrix, with a heatmap and "best asset per strategy"
- **`combine_signals()`** — AND/OR two or more strategies together (e.g.
  require both to agree before buying, exit on either one's sell)
- **`pool_trades()` / `pooled_edge_table()`** — combine one strategy's trades
  across several assets into one sample, for when no single asset produces
  enough trades to judge fairly
- **`generate_report()`** — writes everything above to a self-contained HTML
  file with charts, tables, and an honest "did anything actually clear the bar"
  section

**Edge criteria** (`meets_edge_criteria()`): ≥50 closed trades, win rate ≥45%,
positive expectancy — all three, not any one. On real data this is a genuinely
high bar; don't be surprised if a single-asset, few-year backtest of a slow
strategy comes up short. That's the tool working correctly, not failing —
widen the search (more assets, pooled trades, a faster-firing strategy) before
concluding nothing works, and treat a strategy that does clear the bar as
worth testing out-of-sample, not as ready to trade.

---

## Phase 4: Web Dashboard (FastAPI + Next.js)

A browser-based version of the backtester, split into a Python API and a
Next.js frontend so either can be deployed independently.

### Run locally

```bash
# Terminal 1 — backend (http://localhost:8000)
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:3000)
cd frontend
npm install
npm run dev
```

The frontend reads the API's base URL from `NEXT_PUBLIC_API_URL`
(`frontend/.env.local`, defaults to `http://localhost:8000`).

### API

| Endpoint | Method | Returns |
|---|---|---|
| `/api/assets` | GET | `["AAPL", "BTC-USD", "SPY"]` |
| `/api/strategies` | GET | `[{id, name}, ...]` for the dropdown |
| `/api/backtest` | POST | `{ticker, strategy, days}` → metrics, trades, equity curve |

`api.py` imports `backtester.py` directly (no duplicated logic) and sanitizes
every response for strict JSON: `NaN`/`Infinity` (an open trade's missing exit
price, an infinite profit factor) become `null`, since those are valid Python
floats but invalid JSON tokens that a browser's `JSON.parse` would choke on.

### Frontend

Control panel (ticker / strategy / days) → metric cards, an equity-vs-buy-&-hold
line chart, a trade P&L histogram, and a trade log table. Dark theme using the
same palette as the Streamlit dashboard and HTML reports, responsive down to
phone width.

### Deployment

Config files are already in place — see `backend/Procfile` + `runtime.txt`
(Railway) and `frontend/netlify.toml` (Netlify, static export via
`output: 'export'` in `next.config.js`, since the whole frontend is
client-rendered with no API routes to need a Node server on Netlify's side).

1. **Backend → Railway**: push to GitHub, "New Project → Deploy from GitHub
   repo" on [railway.app](https://railway.app), set the root directory to
   `backend/`, add a `CORS_ORIGINS` env var once you have the Netlify URL.
2. **Frontend → Netlify**: "New site → Import from Git" on
   [netlify.com](https://netlify.com), set the base directory to `frontend/`,
   add `NEXT_PUBLIC_API_URL` pointing at the Railway URL. Netlify picks up
   `netlify.toml` automatically — no need to also run `.github/workflows/deploy.yml`
   unless you specifically want GitHub Actions to gate the deploy (the workflow
   file explains the tradeoff at the top; running both is redundant).
3. Update `frontend/netlify.toml`'s `NEXT_PUBLIC_API_URL` and the `/api/*`
   redirect target with your real Railway URL once step 1 is deployed, then
   redeploy the frontend.

---

## Using Database (PostgreSQL)

If you want to store data:

### Setup database (one time):
```bash
# Create database
psql -U postgres -c "CREATE DATABASE trading;"

# Create table
psql -U postgres -d trading -c "
CREATE TABLE IF NOT EXISTS trading_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    date TIMESTAMP,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    volume BIGINT,
    sma_20 FLOAT,
    sma_50 FLOAT,
    sma_200 FLOAT,
    rsi FLOAT,
    macd FLOAT,
    macd_signal FLOAT,
    bb_upper FLOAT,
    bb_lower FLOAT,
    UNIQUE(ticker, date)
);
"
```

### Use in your code:
```python
from db_store import TradingDatabase

db = TradingDatabase(password="your_password")
db.connect()
db.store_data("AAPL", df_with_indicators)
db.close()
```

---

## Trading Reality Check

✅ **DO:**
- Start with 1-2 indicators you understand deeply
- Backtest on 1+ years of historical data
- Paper trade for 2-4 weeks before risking real money
- Risk only 1-2% per trade
- Keep a trading journal

❌ **DON'T:**
- Overfit to historical data
- Trade based on one signal
- Leverage on your first trades
- Ignore risk management
- Expect instant profits

---

## Common Tickers to Try

**Stocks:** AAPL, MSFT, GOOGL, TSLA, META
**Crypto:** BTC-USD, ETH-USD, SOL-USD
**Indices:** ^GSPC (S&P 500), ^IXIC (NASDAQ)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'yfinance'"
```bash
pip install -r requirements.txt
```

### Streamlit won't connect to database
- Database connection params are hardcoded in `db_store.py`
- Update `host`, `user`, `password`, `database` to match your setup

### Data looks weird / gaps in chart
- Some tickers may have limited history
- Crypto tickers use hyphen: `BTC-USD` not `BTCUSD`

---

## Next: Paper Trading

With the backtester in place you can find out what *actually* worked vs. what
looks good in hindsight. Before trusting any result, check it honestly:

- Does the edge survive on a ticker you didn't tune it on?
- Does it survive a different date range?
- Is it beating buy & hold, or just tracking it with extra steps?
- How many trades is the win rate based on? Five trades is not evidence.

Phase 5 runs the surviving signals against live market data with fake money.

The goal: Find a repeatable, low-risk edge before you trade real money.
