"""Agent 4 - Price Action Agent (Phase 4).

Detects engulfing patterns and pin bars with explicit body/wick
rules, measures candle strength, and watches breakout potential.
Patterns are only valid on COMPLETED candles.
"""

from dataclasses import dataclass, field

STRATEGY_VERSION = "price-action-agent-4.0.0"

BREAKOUT_UP = "up"
BREAKOUT_DOWN = "down"
BREAKOUT_NONE = "none"


def _o(c) -> float:
    v = getattr(c, "open", None)
    return float(v if v is not None else getattr(c, "o"))


def _h(c) -> float:
    v = getattr(c, "high", None)
    return float(v if v is not None else getattr(c, "h"))


def _l(c) -> float:
    v = getattr(c, "low", None)
    return float(v if v is not None else getattr(c, "l"))


def _c(c) -> float:
    v = getattr(c, "close", None)
    return float(v if v is not None else getattr(c, "c"))


def body(c) -> float:
    return abs(_c(c) - _o(c))


def upper_wick(c) -> float:
    return _h(c) - max(_o(c), _c(c))


def lower_wick(c) -> float:
    return min(_o(c), _c(c)) - _l(c)


def is_bullish_engulfing(prev, cur) -> bool:
    """Previous bearish, current bullish, current body engulfs previous body."""
    if _c(prev) >= _o(prev) or _c(cur) <= _o(cur):
        return False
    return _o(cur) <= _c(prev) and _c(cur) >= _o(prev)


def is_bearish_engulfing(prev, cur) -> bool:
    """Previous bullish, current bearish, current body engulfs previous body."""
    if _c(prev) <= _o(prev) or _c(cur) >= _o(cur):
        return False
    return _o(cur) >= _c(prev) and _c(cur) <= _o(prev)


def is_bullish_pin(c) -> bool:
    """Lower wick >= 2x body, upper wick <= body, close in upper third."""
    b = body(c)
    if b <= 0:
        return False
    rng = _h(c) - _l(c)
    return (lower_wick(c) >= 2 * b and upper_wick(c) <= b
            and _c(c) >= _l(c) + 0.66 * rng)


def is_bearish_pin(c) -> bool:
    """Upper wick >= 2x body, lower wick <= body, close in lower third."""
    b = body(c)
    if b <= 0:
        return False
    rng = _h(c) - _l(c)
    return (upper_wick(c) >= 2 * b and lower_wick(c) <= b
            and _c(c) <= _l(c) + 0.33 * rng)


def candle_strength(c) -> float:
    """Close position within range, scaled to [-1, 1]. 0 = dead centre."""
    rng = _h(c) - _l(c)
    if rng <= 0:
        return 0.0
    return 2 * (_c(c) - _l(c)) / rng - 1


def detect_breakout(candles, lookback: int = 20) -> str:
    """Last close beyond the previous `lookback` completed candles' extreme."""
    if len(candles) < lookback + 1:
        return BREAKOUT_NONE
    prior = candles[-lookback - 1:-1]
    last_close = _c(candles[-1])
    if last_close > max(_h(c) for c in prior):
        return BREAKOUT_UP
    if last_close < min(_l(c) for c in prior):
        return BREAKOUT_DOWN
    return BREAKOUT_NONE


@dataclass
class PriceActionResult:
    pair: str
    timeframe: str
    bullish_engulfing: bool = False
    bearish_engulfing: bool = False
    bullish_pin: bool = False
    bearish_pin: bool = False
    strength: float = 0.0
    breakout: str = BREAKOUT_NONE
    explanations: list[str] = field(default_factory=list)
    strategy_version: str = STRATEGY_VERSION


class PriceActionAgent:
    """Pattern detection on completed candles only (never the forming one)."""

    def __init__(self, engulfing_lookback: int = 5, pin_lookback: int = 3):
        self.engulfing_lookback = engulfing_lookback
        self.pin_lookback = pin_lookback

    def analyze(self, candles, pair: str, timeframe: str) -> PriceActionResult:
        r = PriceActionResult(pair=pair, timeframe=timeframe)
        if len(candles) < 2:
            r.explanations.append("Need at least 2 completed candles.")
            return r

        recent = candles[-(self.engulfing_lookback + 1):]
        for i in range(1, len(recent)):
            prev, cur = recent[i - 1], recent[i]
            if is_bullish_engulfing(prev, cur):
                r.bullish_engulfing = True
            if is_bearish_engulfing(prev, cur):
                r.bearish_engulfing = True
        if r.bullish_engulfing:
            r.explanations.append(
                "Bullish engulfing on a completed candle (buyers overwhelmed "
                "sellers; not a guaranteed reversal).")
        if r.bearish_engulfing:
            r.explanations.append(
                "Bearish engulfing on a completed candle (sellers overwhelmed "
                "buyers; not a guaranteed reversal).")

        for c in candles[-self.pin_lookback:]:
            if is_bullish_pin(c):
                r.bullish_pin = True
            if is_bearish_pin(c):
                r.bearish_pin = True
        if r.bullish_pin:
            r.explanations.append(
                "Bullish pin bar (long lower wick >= 2x body, close in upper third).")
        if r.bearish_pin:
            r.explanations.append(
                "Bearish pin bar (long upper wick >= 2x body, close in lower third).")

        r.strength = candle_strength(candles[-1])
        r.breakout = detect_breakout(candles)
        if r.breakout == BREAKOUT_UP:
            r.explanations.append(
                "Last close broke above the prior 20-candle high (upside breakout watch).")
        elif r.breakout == BREAKOUT_DOWN:
            r.explanations.append(
                "Last close broke below the prior 20-candle low (downside breakout watch).")
        if not r.explanations:
            r.explanations.append("No completed-candle pattern of note.")
        return r
