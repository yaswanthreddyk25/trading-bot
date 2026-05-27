import httpx
import logging
from datetime import datetime
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Asynchronous Telegram notification handler.
    """

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    async def send_signal(self, symbol: str, direction: str, price: float, rsi: float):
        """
        Sends a formatted Markdown alert to the specified Telegram channel.
        """
        emoji = "🟢" if direction == "CALL" else "🔴"
        action = "BUY CALL (HIGHER)" if direction == "CALL" else "BUY PUT (LOWER)"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"{emoji} *{action} SIGNAL*\n\n"
            f"*Asset:* `{symbol.upper()}`\n"
            f"*Entry Price:* `{price:.5f}`\n"
            f"*RSI (14):* `{rsi:.2f}`\n"
            f"*Timestamp:* `{timestamp}`\n\n"
            f"_⚠️ Strictly for analytical purposes._"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.base_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Successfully sent {direction} signal to Telegram.")
                else:
                    logger.error(f"Failed to send Telegram alert: {response.text}")
        except Exception as e:
            logger.error(f"Error communicating with Telegram API: {e}")
