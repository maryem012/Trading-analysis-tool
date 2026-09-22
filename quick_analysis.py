#!/usr/bin/env python3
"""
Quick analysis script — run this for fast checks without the Streamlit dashboard
Usage: python quick_analysis.py AAPL 90
"""

import sys
from data_fetcher import DataFetcher

def main():
    # Get args or use defaults
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    
    print(f"\n🔍 Quick Analysis: {ticker} (last {days} days)\n")
    
    # Fetch and calculate
    fetcher = DataFetcher(ticker)
    df = fetcher.fetch_data(days=days)
    df_indicators = fetcher.add_indicators(df)
    signals = fetcher.get_latest_signals(df_indicators)
    
    # Display results
    print("=" * 60)
    print("CURRENT MARKET STATE")
    print("=" * 60)
    print(f"Timestamp:    {signals['timestamp']}")
    print(f"Close Price:  ${signals['close']:.2f}")
    print(f"RSI (14):     {signals['rsi']:.1f} {'⚠️ OVERBOUGHT' if signals['rsi_overbought'] else '⚠️ OVERSOLD' if signals['rsi_oversold'] else '✓ NEUTRAL'}")
    print(f"MACD:         {signals['macd']:.6f} ({'BULLISH 📈' if signals['macd_bullish'] else 'BEARISH 📉'})")
    print(f"SMA 20:       ${signals['sma_20']:.2f}")
    print(f"SMA 50:       ${signals['sma_50']:.2f}")
    print(f"SMA 200:      ${signals['sma_200']:.2f}")
    
    print("\n" + "=" * 60)
    print("SIGNAL SUMMARY")
    print("=" * 60)
    
    if signals['price_above_sma_50']:
        print("✓ Price is ABOVE SMA 50 (uptrend)")
    else:
        print("✗ Price is BELOW SMA 50 (downtrend)")
    
    if signals['sma_20'] > signals['sma_50']:
        print("✓ SMA 20 > SMA 50 (bullish alignment)")
    else:
        print("✗ SMA 20 < SMA 50 (bearish alignment)")
    
    if signals['macd_bullish']:
        print("✓ MACD is BULLISH (upside momentum)")
    else:
        print("✗ MACD is BEARISH (downside momentum)")
    
    print("\n" + "=" * 60)
    print("RECENT DATA (last 5 candles)")
    print("=" * 60)
    
    recent = df_indicators[['close', 'rsi', 'macd', 'sma_50']].tail(5).round(2)
    print(recent.to_string())
    
    print("\n" + "=" * 60)
    print("💡 TRADING TIPS:")
    print("=" * 60)
    print("• Never trade on ONE indicator alone")
    print("• Wait for MULTIPLE signals to align")
    print("• Start with 1-2% risk per trade")
    print("• Keep a journal of your trades")
    print("• Backtest before risking real money")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
