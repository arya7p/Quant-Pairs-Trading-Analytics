"""
Main application orchestrator
Coordinates data ingestion, storage, resampling, and analytics
"""
import asyncio
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from src.data_ingestion import BinanceWSCollector, TickBuffer
from src.storage import DataStore
from src.resampler import DataResampler
from src.analytics import PairsAnalytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketDataPipeline:
    
    def __init__(
        self,
        symbols: List[str],
        db_path: str = "market_data.db",
        buffer_size: int = 100000
    ):
        self.symbols = symbols
        self.tick_buffer = TickBuffer(max_size=buffer_size)
        self.data_store = DataStore(db_path=db_path)
        self.resampler = DataResampler()
        self.analytics = PairsAnalytics()
        self.collector = None
        self.running = False
        
        # Background tasks
        self.persist_task = None
        self.resample_task = None
    
    async def _tick_callback(self, tick: dict):
        await self.tick_buffer.add(tick)
    
    async def _persist_ticks_periodically(self, interval: int = 10):
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                ticks = await self.tick_buffer.get_all()
                
                if ticks:
                    # Save to database
                    self.data_store.insert_ticks_batch(ticks)
                    logger.info(f"Persisted {len(ticks)} ticks to database")
                    
            except Exception as e:
                logger.error(f"Error persisting ticks: {e}")
    
    async def _resample_periodically(
        self,
        timeframes: List[str],
        interval: int = 5
    ):
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                # Get recent ticks from buffer
                ticks = await self.tick_buffer.get_all()
                
                if not ticks:
                    continue
                
                df = pd.DataFrame(ticks)
                
                for symbol in self.symbols:
                    for timeframe in timeframes:
                        try:
                            resampled = self.resampler.resample_ticks(
                                df,
                                timeframe,
                                symbol
                            )
                            
                            if not resampled.empty:
                                self.data_store.insert_resampled(resampled, timeframe)
                                logger.debug(f"Resampled {symbol} to {timeframe}")
                        except Exception as e:
                            logger.error(f"Error resampling {symbol} {timeframe}: {e}")
                
            except Exception as e:
                logger.error(f"Error in resampling task: {e}")
    
    async def start(self, timeframes: List[str] = ['1s', '1m', '5m']):
        self.running = True
        
        self.collector = BinanceWSCollector(
            symbols=self.symbols,
            callback=self._tick_callback
        )
        
        collector_task = asyncio.create_task(self.collector.start())
        self.persist_task = asyncio.create_task(self._persist_ticks_periodically())
        self.resample_task = asyncio.create_task(
            self._resample_periodically(timeframes)
        )
        
        logger.info(f"Pipeline started for symbols: {self.symbols}")
        
        await asyncio.gather(
            collector_task,
            self.persist_task,
            self.resample_task,
            return_exceptions=True
        )
    
    async def stop(self):
        logger.info("Stopping pipeline...")
        self.running = False
        
        if self.collector:
            await self.collector.stop()
        
        if self.persist_task:
            self.persist_task.cancel()
        if self.resample_task:
            self.resample_task.cancel()
        
        logger.info("Pipeline stopped")
    
    def stop_sync(self):
        logger.info("Stopping pipeline (sync)...")
        self.running = False
        
        if self.collector:
            self.collector.running = False
        
        if self.persist_task:
            self.persist_task.cancel()
        if self.resample_task:
            self.resample_task.cancel()
        
        logger.info("Pipeline stopped (sync)")
    
    def get_recent_ticks(
        self,
        symbol: Optional[str] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        return self.data_store.get_ticks(symbol=symbol, limit=limit)
    
    def get_resampled_data(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500
    ) -> pd.DataFrame:
        return self.data_store.get_resampled(symbol, timeframe, limit=limit)
    
    def calculate_pairs_analytics(
        self,
        symbol_a: str,
        symbol_b: str,
        timeframe: str,
        window: int = 20,
        limit: int = 500
    ) -> dict:
        # Get resampled data
        data_a = self.get_resampled_data(symbol_a, timeframe, limit)
        data_b = self.get_resampled_data(symbol_b, timeframe, limit)
        
        if data_a.empty or data_b.empty:
            return {}
        
        # Extract close prices
        price_a = data_a['close']
        price_b = data_b['close']
        
        # Align timestamps
        df = pd.DataFrame({'a': price_a, 'b': price_b}).dropna()
        
        if len(df) < 10:
            return {}
        
        # Calculate hedge ratio
        beta, alpha, r_squared = self.analytics.calculate_hedge_ratio_ols(
            df['a'], df['b']
        )
        
        # Calculate spread
        spread = self.analytics.calculate_spread(df['a'], df['b'], beta)
        
        # Calculate z-score
        z_score = self.analytics.calculate_z_score(spread, window)
        
        # Calculate correlation
        correlation = self.analytics.calculate_correlation(df['a'], df['b'])
        rolling_corr = self.analytics.calculate_rolling_correlation(df['a'], df['b'], window)
        
        # Price statistics
        stats_a = self.analytics.calculate_price_statistics(df['a'], window)
        stats_b = self.analytics.calculate_price_statistics(df['b'], window)
        
        # Half-life
        half_life = self.analytics.calculate_half_life(spread)
        
        return {
            'hedge_ratio': {
                'beta': beta,
                'alpha': alpha,
                'r_squared': r_squared
            },
            'spread': spread,
            'z_score': z_score,
            'correlation': correlation,
            'rolling_correlation': rolling_corr,
            'price_a': df['a'],
            'price_b': df['b'],
            'ohlcv_a': data_a,
            'ohlcv_b': data_b,
            'stats_a': stats_a,
            'stats_b': stats_b,
            'half_life': half_life,
            'timestamps': df.index
        }
    
    def run_adf_test(self, spread: pd.Series) -> dict:
        return self.analytics.adf_test(spread)
    
    def close(self):
        self.data_store.close()
