import pandas as pd
from datetime import datetime
from typing import Optional

# PostgreSQL is optional — importing this module should not require the driver,
# so the error is raised only if you actually try to connect
try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None

class TradingDatabase:
    """
    Store and retrieve trading data from PostgreSQL
    
    Database setup (run once):
    ```
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
    
    CREATE INDEX idx_ticker_date ON trading_data(ticker, date);
    ```
    """
    
    def __init__(self, host: str = "localhost", user: str = "postgres", 
                 password: str = "your_password", database: str = "trading"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed — run `pip install psycopg2-binary` "
                "to use the database, or skip it (storage is optional)."
            )
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("✓ Connected to database")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def store_data(self, ticker: str, df: pd.DataFrame):
        """
        Store OHLCV + indicator data in database
        
        Args:
            ticker: Stock ticker symbol
            df: DataFrame with OHLCV and indicator columns
        """
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            for idx, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO trading_data 
                    (ticker, date, open, high, low, close, volume, sma_20, sma_50, sma_200, rsi, macd, macd_signal, bb_upper, bb_lower)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        close = EXCLUDED.close,
                        rsi = EXCLUDED.rsi,
                        macd = EXCLUDED.macd,
                        sma_50 = EXCLUDED.sma_50
                """, (
                    ticker, idx, row['open'], row['high'], row['low'], 
                    row['close'], row['volume'],
                    row.get('sma_20'), row.get('sma_50'), row.get('sma_200'),
                    row.get('rsi'), row.get('macd'), row.get('macd_signal'),
                    row.get('bb_upper'), row.get('bb_lower')
                ))
            
            self.conn.commit()
            print(f"✓ Stored {len(df)} records for {ticker}")
        
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error storing data: {e}")
            raise
        finally:
            cursor.close()
    
    def get_data(self, ticker: str, days: int = 365) -> pd.DataFrame:
        """
        Retrieve data from database
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days back to retrieve
            
        Returns:
            DataFrame with stored data
        """
        if not self.conn:
            self.connect()
        
        query = f"""
            SELECT * FROM trading_data 
            WHERE ticker = %s 
            AND date >= NOW() - INTERVAL '{days} days'
            ORDER BY date
        """
        
        df = pd.read_sql(query, self.conn, params=(ticker,), parse_dates=['date'])
        df.set_index('date', inplace=True)
        
        return df
