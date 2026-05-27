import pandas as pd
import numpy as np
from typing import Tuple, Optional
from config import settings

class TechnicalAnalysis:
    """
    Handles TA calculations including RSI, SMA, and Support/Resistance.
    """

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_sma(series: pd.Series, period: int = 200) -> pd.Series:
        """Calculates Simple Moving Average."""
        return series.rolling(window=period).mean()

    @staticmethod
    def find_levels(df: pd.DataFrame, variance_threshold: float) -> Tuple[Optional[float], Optional[float]]:
        if len(df) < settings.LOOKBACK_WINDOW:
            return None, None
        window = df.tail(settings.LOOKBACK_WINDOW)
        support = TechnicalAnalysis._get_best_level(window['low'].values, True, variance_threshold)
        resistance = TechnicalAnalysis._get_best_level(window['high'].values, False, variance_threshold)
        return support, resistance

    @staticmethod
    def _get_best_level(prices: np.ndarray, is_support: bool, variance_threshold: float) -> Optional[float]:
        min_touches = settings.MIN_TOUCHES
        levels = []
        for level in prices:
            touches = sum(1 for p in prices if (abs(p - level) / level) <= variance_threshold)
            if touches >= min_touches:
                levels.append(level)
        if not levels: return None
        return min(levels) if is_support else max(levels)

    @staticmethod
    def analyze_market(df: pd.DataFrame, variance_threshold: float) -> dict:
        current_price = df['close'].iloc[-1] if not df.empty else None

        # Check if we have enough data for the 200 SMA
        if len(df) < 200:
            return {
                "rsi": None, "support": None, "resistance": None,
                "sma_200": None, "current_price": current_price
            }

        rsi = TechnicalAnalysis.calculate_rsi(df['close']).iloc[-1]
        sma_200 = TechnicalAnalysis.calculate_sma(df['close'], period=200).iloc[-1]
        support, resistance = TechnicalAnalysis.find_levels(df, variance_threshold)

        return {
            "rsi": rsi,
            "support": support,
            "resistance": resistance,
            "sma_200": sma_200,
            "current_price": current_price
        }
