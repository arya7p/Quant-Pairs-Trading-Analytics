"""
Data resampling engine
Converts tick data to OHLCV bars at different timeframes
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataResampler:
    """
    Resamples tick data to OHLCV bars
    Supports multiple timeframes: 1s, 1m, 5m, 15m, 1h
    """
    
    SUPPORTED_TIMEFRAMES = {
        '1s': '1s',
        '1m': '1min',
        '5m': '5min',
        '15m': '15min',
        '1h': '1h'
    }
    
    def __init__(self):
        """
        Initialize resampler
        """
        pass
    
    def resample_ticks(
        self, 
        df: pd.DataFrame, 
        timeframe: str,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Resample tick data to OHLCV bars
        
        Args:
            df: DataFrame with columns [timestamp, symbol, price, size]
            timeframe: Timeframe string (e.g., '1s', '1m', '5m')
            symbol: Optional symbol filter
            
        Returns:
            DataFrame with OHLCV data indexed by timestamp
        """
        if df.empty:
            return pd.DataFrame()
        
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}. "
                           f"Supported: {list(self.SUPPORTED_TIMEFRAMES.keys())}")
        
        # Filter by symbol if specified
        if symbol:
            df = df[df['symbol'] == symbol].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Set timestamp as index
        df = df.set_index('timestamp')
        
        # Get pandas resample frequency
        freq = self.SUPPORTED_TIMEFRAMES[timeframe]
        
        # Resample to OHLCV
        resampled = pd.DataFrame()
        
        # Price: OHLC
        price_ohlc = df['price'].resample(freq).agg(['first', 'max', 'min', 'last'])
        price_ohlc.columns = ['open', 'high', 'low', 'close']
        
        # Volume: sum of sizes
        volume = df['size'].resample(freq).sum()
        
        # Trade count
        trade_count = df['price'].resample(freq).count()
        
        # Combine
        resampled = pd.concat([price_ohlc, volume, trade_count], axis=1)
        resampled.columns = ['open', 'high', 'low', 'close', 'volume', 'trade_count']
        
        # Remove incomplete bars (last bar might be incomplete)
        # Keep it for live updates
        
        # Remove NaN rows (bars with no data)
        resampled = resampled.dropna(subset=['open', 'close'])
        
        # Add symbol column
        if symbol:
            resampled['symbol'] = symbol
        elif 'symbol' in df.columns:
            # Use most common symbol in each bar
            resampled['symbol'] = df['symbol'].resample(freq).agg(lambda x: x.mode()[0] if len(x) > 0 else None)
        
        # Reset index to make timestamp a column
        resampled = resampled.reset_index()
        
        logger.debug(f"Resampled {len(df)} ticks to {len(resampled)} {timeframe} bars")
        
        return resampled
    
    def resample_multiple_symbols(
        self,
        df: pd.DataFrame,
        timeframe: str,
        symbols: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        Resample multiple symbols separately
        
        Args:
            df: DataFrame with tick data
            timeframe: Timeframe string
            symbols: List of symbols to resample
            
        Returns:
            Dictionary mapping symbol to resampled DataFrame
        """
        result = {}
        
        for symbol in symbols:
            symbol_data = self.resample_ticks(df, timeframe, symbol)
            if not symbol_data.empty:
                result[symbol] = symbol_data
        
        return result
    
    def get_latest_bars(
        self,
        df: pd.DataFrame,
        timeframe: str,
        symbol: str,
        n_bars: int = 100
    ) -> pd.DataFrame:
        """
        Get the latest N resampled bars
        
        Args:
            df: Tick data DataFrame
            timeframe: Timeframe string
            symbol: Symbol to resample
            n_bars: Number of latest bars to return
            
        Returns:
            DataFrame with latest N bars
        """
        resampled = self.resample_ticks(df, timeframe, symbol)
        
        if resampled.empty:
            return resampled
        
        # Return latest n_bars
        return resampled.tail(n_bars)
    
    def calculate_vwap(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Calculate Volume-Weighted Average Price (VWAP)
        
        Args:
            df: Tick data DataFrame with [timestamp, price, size]
            timeframe: Timeframe for VWAP calculation
            
        Returns:
            DataFrame with VWAP values
        """
        if df.empty:
            return pd.DataFrame()
        
        # Ensure timestamp index
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')
        
        freq = self.SUPPORTED_TIMEFRAMES[timeframe]
        
        # VWAP = sum(price * volume) / sum(volume)
        pv = (df['price'] * df['size']).resample(freq).sum()
        v = df['size'].resample(freq).sum()
        
        vwap = pv / v
        
        result = pd.DataFrame({'vwap': vwap})
        result = result.dropna()
        
        return result
    
    def merge_ohlcv_data(
        self,
        symbol_a_df: pd.DataFrame,
        symbol_b_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge OHLCV data from two symbols on timestamp
        
        Args:
            symbol_a_df: Resampled data for symbol A
            symbol_b_df: Resampled data for symbol B
            
        Returns:
            Merged DataFrame with suffixes _a and _b
        """
        if symbol_a_df.empty or symbol_b_df.empty:
            return pd.DataFrame()
        
        # Ensure timestamp is index
        if 'timestamp' in symbol_a_df.columns:
            symbol_a_df = symbol_a_df.set_index('timestamp')
        if 'timestamp' in symbol_b_df.columns:
            symbol_b_df = symbol_b_df.set_index('timestamp')
        
        # Merge on timestamp
        merged = symbol_a_df.join(
            symbol_b_df,
            how='inner',
            lsuffix='_a',
            rsuffix='_b'
        )
        
        return merged


class RollingCalculator:
    """
    Calculate rolling statistics on resampled data
    """
    
    @staticmethod
    def rolling_mean(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window).mean()
    
    @staticmethod
    def rolling_std(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window).std()
    
    @staticmethod
    def rolling_volatility(
        prices: pd.Series,
        window: int,
        annualize: bool = False,
        periods_per_year: int = 252
    ) -> pd.Series:
        returns = prices.pct_change()
        volatility = returns.rolling(window=window).std()
        
        if annualize:
            volatility = volatility * np.sqrt(periods_per_year)
        
        return volatility
    
    @staticmethod
    def rolling_correlation(
        series_a: pd.Series,
        series_b: pd.Series,
        window: int
    ) -> pd.Series:
        return series_a.rolling(window=window).corr(series_b)
    
    @staticmethod
    def rolling_covariance(
        series_a: pd.Series,
        series_b: pd.Series,
        window: int
    ) -> pd.Series:
        return series_a.rolling(window=window).cov(series_b)
