"""Agent 2 - Trend Analysis Agent (Phase 2).

Computes EMA(20)/EMA(50), detects swing highs/lows,
classifies market as bullish / bearish / sideways.
Pure standard library - runs on Termux without pandas/numpy.
"""

from dataclasses import dataclass, field

STRATEGY_VERSION = "trend-agent-2.0.0"

BULLISH = "bullish"
BEARISH = "bearish"
SIDEWAYS = "sideways"
INSUFFICIENT = "insufficient_data"


@dataclass
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float


@dataclass
class TrendResult:
    pair: str
    timeframe: str
    ema20: float | None
    ema50: float | None
    swing_highs: list[float] = field(default_factory=list)
    swing_lows: list[float] = field(default_factory=list)
    classification: str = INSUFFICIENT
    reasons: list[str] = field(default_factory=list)
    strategy_version: str = STRATEGY_VERSION


def _ema(values: list[float], period: int) -> float | None:
    """Standard EMA seeded with the SMA of the first `period` values."""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def _swings(candles: list[Candle], lookback: int) -> tuple[list[float], list[float]]:
    """Fractal swings: a point must be higher/lower than BOTH neighbours.

    The last candle is excluded - it may still be forming (no look-ahead).
    """
    highs, lows = [], []
    start = max(1, len(candles) - lookback)
    for i in range(start, len(candles) - 1):
        h, l = candles[i].high, candles[i].low
        if h > candles[i - 1].high and h > candles[i + 1].high:
            highs.append(h)
        if l < candles[i - 1].low and l < candles[i + 1].low:
            lows.append(l)
    return highs, lows


class TrendAgent:
    """Trend classification from completed candles only."""

    def __init__(self, lookback: int = 60, flat_ratio: float = 0.0005):
        self.lookback = lookback
        self.flat_ratio = flat_ratio

    def analyze(self, candles: list[Candle], pair: str, timeframe: str) -> TrendResult:
        result = TrendResult(pair=pair, timeframe=timeframe, ema20=None, ema50=None)
        if not candles:
            result.reasons.append("No candles provided.")
            return result

        closes = [c.close for c in candles]
        result.ema20 = _ema(closes, 20)
        result.ema50 = _ema(closes, 50)
        result.swing_highs, result.swing_lows = _swings(candles, self.lookback)
        last = closes[-1]

        if result.ema20 is None or result.ema50 is None:
            result.classification = INSUFFICIENT
            result.reasons.append(
                f"Need at least 50 completed candles, got {len(candles)}."
            )
            return result

        gap = abs(result.ema20 - result.ema50) / last if last else 0.0

        if gap < self.flat_ratio:
            result.classification = SIDEWAYS
            result.reasons.append(
                f"EMA20 ({result.ema20:.5f}) and EMA50 ({result.ema50:.5f}) are flat (gap {gap:.4%})."
            )
        elif result.ema20 > result.ema50 and last > result.ema20:
            result.classification = BULLISH
        elif result.ema20 < result.ema50 and last < result.ema20:
            result.classification = BEARISH
        else:
            result.classification = SIDEWAYS

        if result.classification in (BULLISH, BEARISH):
            result.reasons.append(
                f"EMA20 ({result.ema20:.5f}) vs EMA50 ({result.ema50:.5f}): "
                f"{'above' if result.ema20 > result.ema50 else 'below'}."
            )
            result.reasons.append(
                f"Last close {last:.5f} is "
                f"{'above' if last > result.ema20 else 'below'} EMA20."
            )

        hi, lo = result.swing_highs, result.swing_lows
        if len(hi) >= 2 and len(lo) >= 2:
            hh = hi[-1] > hi[-2]
            hl = lo[-1] > lo[-2]
            if hh and hl:
                result.reasons.append("Structure: higher highs and higher lows.")
            elif not hh and not hl:
                result.reasons.append("Structure: lower highs and lower lows.")
            else:
                result.reasons.append("Structure: mixed swings (no clear trend).")
        else:
            result.reasons.append("Not enough confirmed swings in lookback window.")

        return result
