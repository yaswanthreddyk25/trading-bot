import asyncio
import json
import logging
import websockets
import httpx
import pandas as pd
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

class DataStreamer:
    """
    Asynchronous WebSocket client to fetch real-time market data.
    Maintains a local buffer of 1-minute candles.
    """

    def __init__(self, symbol, callback):
        self.symbol = symbol.upper()
        self.callback = callback
        self.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.is_running = False

    async def start(self):
        """
        Connects to the websocket and listens for price updates.
        """
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    logger.info(f"Connected to {self.url}")

                    # Example subscription message (Exchange dependent)
                    # subscribe_msg = {"action": "subscribe", "params": settings.TARGET_ASSET}
                    # await ws.send(json.dumps(subscribe_msg))

                    async for message in ws:
                        data = json.loads(message)
                        await self._process_data(data)

            except Exception as e:
                logger.error(f"WebSocket error: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _process_data(self, data: dict):
        """
        Parses incoming ticks and aggregates them into 1-minute candles.
        This is a template - actual parsing depends on the data provider's JSON structure.
        """
        # Logic to convert raw ticks -> 1m Candles
        # For this example, we assume 'data' contains a closed candle or a tick
        # Implementation of candle aggregation goes here...
        pass

    def add_candle(self, candle: dict):
        """
        Helper to append a completed candle to the dataframe and maintain size.
        """
        new_row = pd.DataFrame([candle])
        self.df = pd.concat([self.df, new_row], ignore_index=True)

        # Keep only necessary lookback to save memory
        if len(self.df) > settings.LOOKBACK_WINDOW * 2:
            self.df = self.df.tail(settings.LOOKBACK_WINDOW * 2)

    async def notify_callback(self):
        await self.callback(self.symbol, self.df)

class BinanceStreamer(DataStreamer):
    """
    Real-time Binance WebSocket client for 1-minute kline data.
    """
    async def fetch_historical_data(self):
        """
        Fetches the last 300 1-minute candles from Binance REST API.
        """
        url = f"https://api.binance.com/api/v3/klines?symbol={self.symbol.upper()}&interval=1m&limit=300"

        logger.info(f"Fetching historical data for {self.symbol}...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    klines = response.json()
                    for k in klines:
                        candle = {
                            'timestamp': datetime.fromtimestamp(k[0] / 1000),
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        }
                        self.add_candle(candle)
                    logger.info(f"Successfully loaded {len(klines)} historical candles for {self.symbol}.")
                    await self.notify_callback()
                else:
                    logger.error(f"Failed to fetch history for {self.symbol}: {response.text}")
        except Exception as e:
            logger.error(f"Error fetching historical data for {self.symbol}: {e}")

    async def start(self):
        self.is_running = True
        # Fetch history first to eliminate warmup wait
        await self.fetch_historical_data()

        # Binance kline stream URL
        url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@kline_1m"
        logger.info(f"Connecting to Binance Live Stream for {self.symbol}: {url}")

        while self.is_running:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to Binance Live for {self.symbol}")
                    async for message in ws:
                        if not self.is_running:
                            await ws.close()
                            break

                        data = json.loads(message)
                        kline = data.get('k', {})
                        if kline.get('x'):
                            candle = {
                                'timestamp': datetime.fromtimestamp(kline['t'] / 1000),
                                'open': float(kline['o']),
                                'high': float(kline['h']),
                                'low': float(kline['l']),
                                'close': float(kline['c']),
                                'volume': float(kline['v'])
                            }
                            self.add_candle(candle)
                            await self.notify_callback()
            except Exception as e:
                if self.is_running:
                    logger.error(f"Binance Stream Error: {e}. Reconnecting...")
                    await asyncio.sleep(5)
                else:
                    break

    def stop(self):
        self.is_running = False

class MockStreamer(DataStreamer):
    """
    Mock streamer for testing without a live API key.
    Generates random price data every few seconds.
    """
    async def start(self):
        logger.info("Starting Mock Streamer (Warmup: Pre-filling 60 candles)...")
        import random
        from datetime import timedelta

        base_price = 35.500
        # Pre-fill 60 candles so indicators work immediately
        for i in range(60):
            candle = {
                'timestamp': datetime.now() - timedelta(minutes=(60-i)),
                'open': base_price + random.uniform(-0.01, 0.01),
                'high': base_price + random.uniform(0.01, 0.05),
                'low': base_price - random.uniform(0.01, 0.05),
                'close': base_price + random.uniform(-0.02, 0.02),
                'volume': random.randint(100, 1000)
            }
            base_price = candle['close']
            self.add_candle(candle)

        logger.info("Warmup complete. Starting live simulation...")
        while True:
            # Simulate a 1-minute candle closing
            candle = {
                'timestamp': datetime.now(),
                'open': base_price + random.uniform(-0.01, 0.01),
                'high': base_price + random.uniform(0.01, 0.05),
                'low': base_price - random.uniform(0.01, 0.05),
                'close': base_price + random.uniform(-0.02, 0.02),
                'volume': random.randint(100, 1000)
            }
            base_price = candle['close']

            self.add_candle(candle)
            await self.callback(self.df)

            # Simulate 1-minute wait (speed up for testing if desired)
            await asyncio.sleep(60)
