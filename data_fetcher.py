from __future__ import annotations

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple

class DataFetcher:
    """Fetch and cache market data from yfinance"""
    
    def __init__(self, ticker: str = "AAPL"):
        self.ticker = ticker
        self.data = None
    
    def fetch_data(self, days: int = 365) -> pd.DataFrame:
        """
        Fetch OHLCV data for the last N days
        
        Args:
            days: Number of days of historical data
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        print(f"Fetching {self.ticker} data from {start_date.date()} to {end_date.date()}...")
        
        self.data = yf.download(
            self.ticker,
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=True
        )
        
        self.data = self.normalize_columns(self.data)

        print(f"Fetched {len(self.data)} candles")
        return self.data

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Flatten yfinance's column layout to plain lowercase names.

        Newer yfinance versions return MultiIndex columns (field, ticker) even for
        a single-ticker download, so the field level has to be pulled out first.
        """
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower().replace(' ', '_') for col in df.columns]

        # yfinance can include a trailing row for the current (still in
        # progress, or not-yet-opened) trading day with an all-NaN close —
        # not usable data, and silently corrupts whatever reads the "latest"
        # bar (signals, backtests, the dashboard) if left in. Every caller
        # (DataFetcher.fetch_data and strategy_lab.get_price_data) routes
        # through this method, so fixing it here covers both.
        if 'close' in df.columns:
            df = df[df['close'].notna()]
        return df

    def add_indicators(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Calculate technical indicators
        
        Args:
            df: DataFrame with OHLCV data (uses self.data if None)
            
        Returns:
            DataFrame with added indicator columns
        """
        if df is None:
            df = self.data.copy()
        else:
            df = df.copy()
        
        if df is None or len(df) == 0:
            raise ValueError("No data available. Call fetch_data() first.")
        
        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Exponential Moving Average
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD (Moving Average Convergence Divergence)
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI (Relative Strength Index)
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # Bollinger Bands
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = sma_20 + (std_20 * 2)
        df['bb_middle'] = sma_20
        df['bb_lower'] = sma_20 - (std_20 * 2)
        
        # Price change percentage
        df['pct_change'] = df['close'].pct_change() * 100
        
        return df
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_latest_signals(self, df: pd.DataFrame) -> dict:
        """
        Extract latest indicator values and generate basic signals
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary with latest values and signals
        """
        latest = df.iloc[-1]
        
        signals = {
            'timestamp': df.index[-1],
            'close': latest['close'],
            'rsi': latest['rsi'],
            'macd': latest['macd'],
            'macd_signal': latest['macd_signal'],
            'sma_20': latest['sma_20'],
            'sma_50': latest['sma_50'],
            'sma_200': latest['sma_200'],
            
            # Simple signal logic (you'll refine this)
            'rsi_overbought': latest['rsi'] > 70 if pd.notna(latest['rsi']) else None,
            'rsi_oversold': latest['rsi'] < 30 if pd.notna(latest['rsi']) else None,
            'macd_bullish': latest['macd'] > latest['macd_signal'] if pd.notna(latest['macd']) else None,
            'price_above_sma_50': latest['close'] > latest['sma_50'] if pd.notna(latest['sma_50']) else None,
        }
        
        return signals
