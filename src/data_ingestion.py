"""
WebSocket data ingestion module for Binance Futures
"""
import asyncio
import json
import websockets
from datetime import datetime
from typing import List, Callable, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BinanceWSCollector:
    """
    Asynchronous WebSocket collector for Binance Futures tick data
    """
    
    def __init__(self, symbols: List[str], callback: Callable):
        self.symbols = [s.lower() for s in symbols]
        self.callback = callback
        self.tasks = []
        self.running = False
        
    def normalize_tick(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.fromtimestamp(raw_data['T'] / 1000.0)
        
        return {
            'timestamp': timestamp,
            'symbol': raw_data['s'].lower(),
            'price': float(raw_data['p']),
            'size': float(raw_data['q']),
            'is_buyer_maker': raw_data['m']
        }
    
    async def _subscribe_symbol(self, symbol: str):
        url = f"wss://fstream.binance.com/ws/{symbol}@trade"
        
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to {symbol}")
                    
                    async for message in ws:
                        if not self.running:
                            break
                            
                        try:
                            data = json.loads(message)
                            
                            if data.get('e') == 'trade':
                                normalized = self.normalize_tick(data)
                                await self.callback(normalized)
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error for {symbol}: {e}")
                        except Exception as e:
                            logger.error(f"Error processing message for {symbol}: {e}")
                            
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error for {symbol}: {e}")
                if self.running:
                    logger.info(f"Reconnecting to {symbol} in 5 seconds...")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error for {symbol}: {e}")
                if self.running:
                    await asyncio.sleep(5)
    
    async def start(self):
        self.running = True
        logger.info(f"Starting collection for symbols: {self.symbols}")
        
        self.tasks = [
            asyncio.create_task(self._subscribe_symbol(symbol))
            for symbol in self.symbols
        ]
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop(self):
        logger.info("Stopping collector...")
        self.running = False
        
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Collector stopped")


class TickBuffer:
    """
    Thread-safe buffer for storing tick data
    """
    
    def __init__(self, max_size: int = 100000):
        self.buffer = []
        self.max_size = max_size
        self.lock = asyncio.Lock()
    
    async def add(self, tick: Dict[str, Any]):
        async with self.lock:
            self.buffer.append(tick)
            
            # Keep buffer size manageable
            if len(self.buffer) > self.max_size:
                self.buffer = self.buffer[-self.max_size:]
    
    async def get_all(self) -> List[Dict[str, Any]]:
        async with self.lock:
            return self.buffer.copy()
    
    async def clear(self):
        async with self.lock:
            self.buffer.clear()
    
    async def size(self) -> int:
        async with self.lock:
            return len(self.buffer)
