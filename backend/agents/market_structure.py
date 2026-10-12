"""Agent 5 - Market Structure Agent (Phase 5).

Swing points, support/resistance zones (clustered levels),
structure state, and structure breaks.
Uses completed candles only - no look-ahead bias.
"""

from dataclasses import dataclass, field

STRATEGY_VERSION = "structure-agent-5.0.0"

UPTREND = "uptrend"
DOWNTREND = "downtrend"
RANGING = "ranging"
NO_BREAK = "none"
BULL_BREAK = "bullish_break"
BEAR_BREAK = "bearish_break"


def _h(c) -> float:
    v = getattr(c, "high", None)
    return float(v if v is not None else getattr(c, "h"))


def _l(c) -> float:
    v = getattr(c, "low", None)
    return float(v if v is not None else getattr(c, "l"))


def _c(c) -> float:
    v = getattr(c, "close", None)
    return float(v if v is not None else getattr(c, "c"))


def find_swings(candles, lookback: int = 60):
    """Fractal swings; last candle excluded (may still be forming)."""
    highs, lows = [], []
    start = max(1, len(candles) - lookback)
    for i in range(start, len(candles) - 1):
        h, l = _h(candles[i]), _l(candles[i])
        if h > _h(candles[i - 1]) and h > _h(candles[i + 1]):
            highs.append(h)
        if l < _l(candles[i - 1]) and l < _l(candles[i + 1]):
            lows.append(l)
    return highs, lows


def cluster_zones(levels, tolerance: float):
    """Group nearby swing levels into zones (centre, band, touch count)."""
    zones = []
    for lv in sorted(levels):
        if zones and abs(lv - zones[-1]["center"]) <= tolerance:
            z = zones[-1]
            z["touches"] += 1
            z["high"] = max(z["high"], lv)
            z["low"] = min(z["low"], lv)
            z["center"] = (z["center"] * (z["touches"] - 1) + lv) / z["touches"]
        else:
            zones.append({"center": lv, "low": lv, "high": lv, "touches": 1})
    return zones


@dataclass
class StructureResult:
    pair: str
    timeframe: str
    swing_highs: list = field(default_factory=list)
    swing_lows: list = field(default_factory=list)
    resistance_zones: list = field(default_factory=list)
    support_zones: list = field(default_factory=list)
    structure: str = RANGING
    break_event: str = NO_BREAK
    explanations: list[str] = field(default_factory=list)
    strategy_version: str = STRATEGY_VERSION


class MarketStructureAgent:
    def __init__(self, lookback: int = 60, zone_tolerance: float = 0.0005):
        self.lookback = lookback
        self.zone_tolerance = zone_tolerance

    def analyze(self, candles, pair: str, timeframe: str) -> StructureResult:
        r = StructureResult(pair=pair, timeframe=timeframe)
        if len(candles) < 5:
            r.explanations.append("Need at least 5 completed candles.")
            return r

        r.swing_highs, r.swing_lows = find_swings(candles, self.lookback)
        ref = abs(_c(candles[-1])) or 1.0
        tol = ref * self.zone_tolerance
        r.resistance_zones = sorted(cluster_zones(r.swing_highs, tol),
                                    key=lambda z: -z["touches"])[:3]
        r.support_zones = sorted(cluster_zones(r.swing_lows, tol),
                                 key=lambda z: -z["touches"])[:3]

        if len(r.swing_highs) >= 2 and len(r.swing_lows) >= 2:
            hh = r.swing_highs[-1] > r.swing_highs[-2]
            hl = r.swing_lows[-1] > r.swing_lows[-2]
            if hh and hl:
                r.structure = UPTREND
                r.explanations.append(
                    "Structure: higher highs + higher lows (uptrend).")
            elif not hh and not hl:
                r.structure = DOWNTREND
                r.explanations.append(
                    "Structure: lower highs + lower lows (downtrend).")
            else:
                r.explanations.append("Structure: mixed swings (ranging).")
        else:
            r.explanations.append("Not enough swings to classify structure.")

        last_close = _c(candles[-1])
        if r.swing_highs and last_close > r.swing_highs[-1]:
            r.break_event = BULL_BREAK
            r.explanations.append(
                f"Close {last_close:.5f} above last swing high "
                f"{r.swing_highs[-1]:.5f}: bullish structure break.")
        elif r.swing_lows and last_close < r.swing_lows[-1]:
            r.break_event = BEAR_BREAK
            r.explanations.append(
                f"Close {last_close:.5f} below last swing low "
                f"{r.swing_lows[-1]:.5f}: bearish structure break.")
        else:
            r.explanations.append("No structure break at last completed close.")

        if r.resistance_zones:
            z = r.resistance_zones[0]
            r.explanations.append(
                f"Nearest resistance zone {z['low']:.5f}-{z['high']:.5f} "
                f"({z['touches']} touches).")
        if r.support_zones:
            z = r.support_zones[0]
            r.explanations.append(
                f"Nearest support zone {z['low']:.5f}-{z['high']:.5f} "
                f"({z['touches']} touches).")
        return r
