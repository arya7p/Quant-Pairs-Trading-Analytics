"""
Data storage layer using SQLite
Stores tick data and resampled OHLCV data
"""
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DataStore:
    """
    SQLite-based storage for tick and resampled data
    Simple and effective for single-machine deployment
    Can be replaced with TimescaleDB/Redis for production scaling
    """
    
    def __init__(self, db_path: str = "market_data.db"): 
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Create ticks table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                is_buyer_maker INTEGER
            )
        """)
        
        # Create index for ticks
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON ticks(symbol, timestamp)
        """)
        
        # Create resampled data table (OHLCV)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS resampled (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                trade_count INTEGER,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        # Create index for resampled
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_resampled_lookup 
            ON resampled(symbol, timeframe, timestamp)
        """)
        
        # Create alerts log table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                alert_type TEXT NOT NULL,
                symbol TEXT,
                message TEXT NOT NULL,
                value REAL,
                threshold REAL
            )
        """)
        
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def insert_tick(self, tick: Dict[str, Any]):
        try:
            self.conn.execute("""
                INSERT INTO ticks (timestamp, symbol, price, size, is_buyer_maker)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tick['timestamp'],
                tick['symbol'],
                tick['price'],
                tick['size'],
                int(tick.get('is_buyer_maker', 0))
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting tick: {e}")
    
    def insert_ticks_batch(self, ticks: List[Dict[str, Any]]):
        if not ticks:
            return
        
        try:
            data = [
                (t['timestamp'], t['symbol'], t['price'], t['size'], 
                 int(t.get('is_buyer_maker', 0)))
                for t in ticks
            ]
            
            self.conn.executemany("""
                INSERT INTO ticks (timestamp, symbol, price, size, is_buyer_maker)
                VALUES (?, ?, ?, ?, ?)
            """, data)
            self.conn.commit()
            logger.debug(f"Inserted {len(ticks)} ticks")
        except Exception as e:
            logger.error(f"Error inserting ticks batch: {e}")
    
    def get_ticks(
        self, 
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        query = "SELECT timestamp, symbol, price, size, is_buyer_maker FROM ticks WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def insert_resampled(self, df: pd.DataFrame, timeframe: str):
        if df.empty:
            return
        
        try:
            df_copy = df.reset_index()
            
            # Prepare data for insertion
            data = []
            for _, row in df_copy.iterrows():
                # Convert pandas Timestamp to string for SQLite
                timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f') if hasattr(row['timestamp'], 'strftime') else str(row['timestamp'])
                
                data.append((
                    timestamp_str,
                    row['symbol'],
                    timeframe,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume']),
                    int(row.get('trade_count', 0))
                ))
            
            self.conn.executemany("""
                INSERT OR REPLACE INTO resampled 
                (timestamp, symbol, timeframe, open, high, low, close, volume, trade_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            self.conn.commit()
            logger.debug(f"Inserted {len(data)} resampled bars for {timeframe}")
        except Exception as e:
            logger.error(f"Error inserting resampled data: {e}")
    
    def get_resampled(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        limit: Optional[int] = 1000
    ) -> pd.DataFrame:
        query = """
            SELECT timestamp, open, high, low, close, volume, trade_count
            FROM resampled
            WHERE symbol = ? AND timeframe = ?
        """
        params = [symbol, timeframe]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
        
        return df
    
    def log_alert(
        self,
        alert_type: str,
        message: str,
        symbol: Optional[str] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ):
        try:
            self.conn.execute("""
                INSERT INTO alerts (timestamp, alert_type, symbol, message, value, threshold)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now(), alert_type, symbol, message, value, threshold))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
    
    def get_alerts(self, limit: int = 100) -> pd.DataFrame:
        query = """
            SELECT timestamp, alert_type, symbol, message, value, threshold
            FROM alerts
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, self.conn, params=[limit])
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
