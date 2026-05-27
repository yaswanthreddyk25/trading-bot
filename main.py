import asyncio
import logging
import argparse
from config import settings
from indicators import TechnicalAnalysis
from streamer import BinanceStreamer
from notifier import TelegramNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("TradingApp")

class TradingAssistant:
    def __init__(self, symbols, ui_callback=None):
        self.notifier = TelegramNotifier()
        self.ta = TechnicalAnalysis()
        self.symbols = symbols
        self.ui_callback = ui_callback
        self.streamers = [
            BinanceStreamer(symbol=s, callback=self.process_market_update)
            for s in self.symbols
        ]

    async def process_market_update(self, symbol, df):
        # Get variance for this specific asset
        variance = settings.get_variance(symbol)
        analysis = self.ta.analyze_market(df, variance_threshold=variance)

        rsi = analysis['rsi']
        support = analysis['support']
        resistance = analysis['resistance']
        sma_200 = analysis['sma_200']
        price = analysis['current_price']

        if rsi is None or sma_200 is None:
            return

        log_msg = f"[{symbol}] Price: {price:.2f} | RSI: {rsi:.2f} | SMA200: {sma_200:.2f}"
        logger.info(log_msg)
        if self.ui_callback:
            self.ui_callback(log_msg)

        # 🟢 CALL Signal Criteria (Price MUST be ABOVE 200 SMA)
        if support and price <= support and rsi < 30:
            if price > sma_200:
                match_msg = f"🎯 CALL MATCH [{symbol}]: Support + Oversold + Bullish Trend."
                logger.info(match_msg)
                if self.ui_callback: self.ui_callback(f"🟢 {match_msg}")
                await self.notifier.send_signal(symbol, "CALL", price, rsi)
            else:
                logger.warning(f"⚠️ CALL FILTERED [{symbol}]: RSI/Support matched, but Price is BELOW 200 SMA (Bearish Trend).")

        # 🔴 PUT Signal Criteria (Price MUST be BELOW 200 SMA)
        elif resistance and price >= resistance and rsi > 70:
            if price < sma_200:
                match_msg = f"🎯 PUT MATCH [{symbol}]: Resistance + Overbought + Bearish Trend."
                logger.info(match_msg)
                if self.ui_callback: self.ui_callback(f"🔴 {match_msg}")
                await self.notifier.send_signal(symbol, "PUT", price, rsi)
            else:
                logger.warning(f"⚠️ PUT FILTERED [{symbol}]: RSI/Resistance matched, but Price is ABOVE 200 SMA (Bullish Trend).")

    async def run(self):
        logger.info(f"--- Starting Trading Assistant (Trend Filtered) for {', '.join(self.symbols)} ---")
        await asyncio.gather(*(s.start() for s in self.streamers))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trend-Filtered Trading Assistant")
    parser.add_argument("--assets", nargs="+", default=settings.DEFAULT_ASSETS)
    args = parser.parse_args()

    symbols = [s.upper() for s in args.assets]
    app = TradingAssistant(symbols)
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
