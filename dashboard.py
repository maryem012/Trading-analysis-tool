import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from db_store import TradingDatabase
from backtester import BacktestEngine, STRATEGIES
from plots import equity_figure, trades_figure

st.set_page_config(page_title="Trading Analysis Tool", layout="wide")
st.title("📈 Trading Analysis Tool")
st.caption("Phase 1: indicators & signals · Phase 2: strategy backtesting")

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    ticker = st.text_input("Stock Ticker", value="AAPL", help="e.g., AAPL, MSFT, BTC-USD")
    days = st.slider("Days of data", min_value=30, max_value=730, value=365, step=30)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Fetch Data", use_container_width=True):
            st.session_state.fetch_clicked = True
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

# Fetch and process data
if 'fetch_clicked' in st.session_state or True:  # Default load
    try:
        fetcher = DataFetcher(ticker)
        df = fetcher.fetch_data(days=days)
        df_with_indicators = fetcher.add_indicators(df)
        
        # Get latest signals
        signals = fetcher.get_latest_signals(df_with_indicators)
        
        # Display key metrics
        st.header("Current Market Snapshot")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Current Price",
                value=f"${signals['close']:.2f}"
            )
        
        with col2:
            st.metric(
                label="RSI (14)",
                value=f"{signals['rsi']:.1f}",
                delta="Overbought" if signals['rsi_overbought'] else "Oversold" if signals['rsi_oversold'] else "Normal"
            )
        
        with col3:
            st.metric(
                label="MACD",
                value=f"{signals['macd']:.4f}",
                delta="Bullish" if signals['macd_bullish'] else "Bearish"
            )
        
        with col4:
            st.metric(
                label="Price vs SMA50",
                value=f"${signals['close']:.2f}",
                delta=f"${signals['close'] - signals['sma_50']:.2f}" if signals['sma_50'] else "N/A"
            )
        
        with col5:
            last_close = df_with_indicators['close'].iloc[-1]
            prev_close = df_with_indicators['close'].iloc[-2] if len(df_with_indicators) > 1 else last_close
            pct_change = ((last_close - prev_close) / prev_close * 100)
            st.metric(
                label="Today's Change",
                value=f"{pct_change:.2f}%",
                delta=f"${last_close - prev_close:.2f}"
            )
        
        # Charts
        st.header("Technical Analysis")
        
        # Chart 1: Price + Moving Averages
        fig1 = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3],
            subplot_titles=("Price & Moving Averages", "Volume")
        )
        
        # Price line
        fig1.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['close'],
                      name="Close", line=dict(color='white', width=2)),
            row=1, col=1
        )
        
        # SMAs
        fig1.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['sma_20'],
                      name="SMA 20", line=dict(color='orange', width=1)),
            row=1, col=1
        )
        fig1.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['sma_50'],
                      name="SMA 50", line=dict(color='blue', width=1)),
            row=1, col=1
        )
        fig1.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['sma_200'],
                      name="SMA 200", line=dict(color='red', width=1)),
            row=1, col=1
        )
        
        # Bollinger Bands
        fig1.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['bb_upper'],
                      name="BB Upper", line=dict(color='rgba(100,100,100,0.3)')),
            row=1, col=1
        )
        fig1.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['bb_lower'],
                      name="BB Lower", line=dict(color='rgba(100,100,100,0.3)'),
                      fill='tonexty', fillcolor='rgba(100,100,100,0.1)'),
            row=1, col=1
        )
        
        # Volume
        colors = ['green' if df_with_indicators['close'].iloc[i] >= df_with_indicators['close'].iloc[i-1] 
                 else 'red' for i in range(len(df_with_indicators))]
        fig1.add_trace(
            go.Bar(x=df_with_indicators.index, y=df_with_indicators['volume'],
                  name="Volume", marker=dict(color=colors, opacity=0.5)),
            row=2, col=1
        )
        
        fig1.update_layout(height=600, hovermode='x unified', template='plotly_dark')
        fig1.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig1.update_yaxes(title_text="Volume", row=2, col=1)
        fig1.update_xaxes(title_text="Date", row=2, col=1)
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # Chart 2: RSI + MACD
        fig2 = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            subplot_titles=("RSI (14)", "MACD")
        )
        
        # RSI
        fig2.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['rsi'],
                      name="RSI", line=dict(color='purple', width=2)),
            row=1, col=1
        )
        fig2.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought", row=1, col=1)
        fig2.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold", row=1, col=1)
        
        # MACD
        fig2.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['macd'],
                      name="MACD", line=dict(color='blue', width=2)),
            row=2, col=1
        )
        fig2.add_trace(
            go.Scatter(x=df_with_indicators.index, y=df_with_indicators['macd_signal'],
                      name="Signal", line=dict(color='red', width=2)),
            row=2, col=1
        )
        fig2.add_trace(
            go.Bar(x=df_with_indicators.index, y=df_with_indicators['macd_histogram'],
                  name="Histogram", marker=dict(color='gray', opacity=0.3)),
            row=2, col=1
        )
        
        fig2.update_layout(height=500, hovermode='x unified', template='plotly_dark')
        fig2.update_yaxes(title_text="RSI", row=1, col=1)
        fig2.update_yaxes(title_text="MACD", row=2, col=1)
        fig2.update_xaxes(title_text="Date", row=2, col=1)
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Data table
        st.header("Raw Data")
        
        # Show last 20 rows
        display_cols = ['open', 'high', 'low', 'close', 'volume', 'sma_20', 'sma_50', 'rsi', 'macd']
        st.dataframe(
            df_with_indicators[display_cols].tail(20).astype(float).round(2),
            use_container_width=True
        )
        
        # Signals summary
        st.header("Current Signals Summary")
        
        signal_summary = f"""
        **Momentum Signals:**
        - RSI: {signals['rsi']:.1f} {'🔴 OVERBOUGHT' if signals['rsi_overbought'] else '🟢 OVERSOLD' if signals['rsi_oversold'] else '⚪ NEUTRAL'}
        - MACD: {'🔵 BULLISH' if signals['macd_bullish'] else '🔴 BEARISH'}
        
        **Trend Signals:**
        - Price vs SMA50: {'📈 ABOVE' if signals['price_above_sma_50'] else '📉 BELOW'}
        - SMA 20 vs SMA 50: {'⬆️ BULLISH' if signals['sma_20'] > signals['sma_50'] else '⬇️ BEARISH'}
        
        *Remember: Use multiple indicators together, never trade on one signal alone!*
        """
        
        st.info(signal_summary)
    
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.info("Make sure the ticker symbol is valid (e.g., AAPL, BTC-USD)")


# ============================================================================
# Phase 2 — Strategy Backtest
# ============================================================================

with st.sidebar:
    st.divider()
    st.header("Backtest Settings")

    bt_strategy_name = st.selectbox("Strategy", list(STRATEGIES.keys()))
    bt_years = st.select_slider("History", options=[0.5, 1, 2, 3, 5], value=1,
                                format_func=lambda y: f"{y:g} yr")
    bt_capital = st.number_input("Initial capital ($)", min_value=500, max_value=1_000_000,
                                 value=10_000, step=500)
    bt_risk = st.slider("Risk per trade (%)", 0.5, 10.0, 2.0, 0.5,
                        help="Percent of equity risked between entry and stop")

    bt_use_stop = st.checkbox("Use stop-loss", value=True)
    bt_stop = st.slider("Stop-loss (%)", 1.0, 20.0, 5.0, 0.5, disabled=not bt_use_stop)
    bt_use_tp = st.checkbox("Use take-profit", value=True)
    bt_tp = st.slider("Take-profit (%)", 1.0, 50.0, 10.0, 0.5, disabled=not bt_use_tp)

    if st.button("▶️ Run Backtest", use_container_width=True, type="primary"):
        st.session_state.run_backtest = True

st.divider()
st.header("🔬 Strategy Backtest")

if st.session_state.pop('run_backtest', False):
    try:
        with st.spinner(f"Backtesting {bt_strategy_name} on {ticker}..."):
            bt_end = pd.Timestamp(datetime.now().date())
            engine = BacktestEngine(
                ticker=ticker,
                start_date=bt_end - timedelta(days=int(365 * bt_years)),
                end_date=bt_end,
                initial_capital=bt_capital,
                risk_per_trade=bt_risk,
                stop_loss_pct=bt_stop if bt_use_stop else None,
                take_profit_pct=bt_tp if bt_use_tp else None,
            )
            st.session_state.backtest_result = engine.run(
                STRATEGIES[bt_strategy_name], strategy_name=bt_strategy_name
            )
    except Exception as e:
        st.session_state.backtest_result = None
        st.error(f"Backtest failed: {e}")

result = st.session_state.get('backtest_result')

if result is None:
    st.info("Pick a strategy under **Backtest Settings** in the sidebar, then hit **Run Backtest**.")
else:
    m = result.metrics
    st.subheader(f"{result.strategy_name} — {result.ticker}")
    st.caption(
        f"{m['start_date']} → {m['end_date']} · {m['bars']} bars · "
        f"${result.initial_capital:,.0f} starting capital · {m['total_trades']} trades"
    )

    # --- Headline metrics -------------------------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Return", f"{m['total_return_pct']:.2f}%",
                  delta=f"{m['total_return_pct'] - m['buy_hold_return_pct']:+.2f}% vs buy & hold")
    with col2:
        st.metric("Win Rate", f"{m['win_rate_pct']:.1f}%",
                  delta=f"{m['winning_trades']}W / {m['losing_trades']}L", delta_color="off")
    with col3:
        pf = "∞" if m['profit_factor'] == float('inf') else f"{m['profit_factor']:.2f}"
        st.metric("Profit Factor", pf, delta="gross profit / gross loss", delta_color="off")
    with col4:
        st.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}",
                  delta="annualized", delta_color="off")
    with col5:
        st.metric("Max Drawdown", f"{m['max_drawdown_pct']:.2f}%",
                  delta=f"{m['avg_trade_duration_days']:.0f}d avg hold", delta_color="off")

    # --- Equity curve + drawdown, then trades on price -------------------
    st.plotly_chart(equity_figure(result), use_container_width=True)
    st.plotly_chart(trades_figure(result), use_container_width=True)

    # --- Tables -----------------------------------------------------------
    trades = result.trades_frame()
    left, right = st.columns([1, 2])

    with left:
        st.subheader("Metrics")
        st.dataframe(result.metrics_frame(), use_container_width=True, hide_index=True)

    with right:
        st.subheader("Trade Log")
        if trades.empty:
            st.info("This strategy produced no trades in the selected window.")
        else:
            log = trades.copy()
            for col in ('entry_date', 'exit_date'):
                log[col] = pd.to_datetime(log[col]).dt.strftime('%Y-%m-%d')
            log = log[['entry_date', 'entry_price', 'exit_date', 'exit_price', 'shares',
                       'profit_loss', 'return_pct', 'duration_days', 'exit_reason']]
            log.columns = ['Entry', 'Entry $', 'Exit', 'Exit $', 'Shares',
                           'P/L $', 'Return %', 'Days', 'Reason']
            st.dataframe(log.round(2), use_container_width=True, hide_index=True)

            if result.open_trades:
                last_close = float(result.data['close'].iloc[-1])
                t = result.open_trades[0]
                st.caption(
                    f"⏳ 1 position still open — entered {t.entry_date.date()} at "
                    f"${t.entry_price:.2f}, marked at ${last_close:.2f} "
                    f"({t.unrealized_pl(last_close):+,.2f} unrealized). "
                    "Trade stats above count closed trades only."
                )

    st.caption(
        "Signals fill at the **next** bar's open, stops and targets are checked against each "
        "bar's low/high, and a bar that hits both is assumed to hit the stop first. "
        "No commissions or slippage — results are optimistic."
    )
