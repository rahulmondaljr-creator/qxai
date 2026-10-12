"""Agent 6 - Volatility and Risk Agent (Phase 6).

Classifies volatility from ATR, flags unusual spikes,
and vetoes trading when data quality fails.
Never invents information that was not provided.
"""

from dataclasses import dataclass, field

from backend.agents.indicators import atr

STRATEGY_VERSION = "risk-agent-6.0.0"

LOW = "low"
NORMAL = "normal"
HIGH = "high"
NO_TRADE = "NO_TRADE"


def _h(c) -> float:
    v = getattr(c, "high", None)
    return float(v if v is not None else getattr(c, "h"))


def _l(c) -> float:
    v = getattr(c, "low", None)
    return float(v if v is not None else getattr(c, "l"))


def _c(c) -> float:
    v = getattr(c, "close", None)
    return float(v if v is not None else getattr(c, "c"))


@dataclass
class RiskResult:
    pair: str
    timeframe: str
    atr14: float | None
    atr_pct: float | None          # ATR as % of price
    volatility_level: str          # low / normal / high
    unusual_spike: bool
    trade_allowed: bool
    explanations: list[str] = field(default_factory=list)
    strategy_version: str = STRATEGY_VERSION


class RiskAgent:
    """Risk gate: stale or missing data -> trade vetoed."""

    def __init__(self, low_below: float = 0.02, high_above: float = 0.08,
                 spike_factor: float = 2.5):
        self.low_below = low_below       # ATR % below this = low volatility
        self.high_above = high_above     # ATR % above this = high volatility
        self.spike_factor = spike_factor  # last range > factor * ATR = spike

    def analyze(self, candles, pair: str, timeframe: str,
                stale: bool = False) -> RiskResult:
        r = RiskResult(pair, timeframe, None, None, LOW, False, False)

        if stale:
            r.trade_allowed = False
            r.explanations.append(
                "Data is stale (feed delayed): trading vetoed.")
        if len(candles) < 15:
            r.trade_allowed = False
            r.explanations.append(
                "Fewer than 15 completed candles: ATR unreliable, trading vetoed.")
            return r

        a = atr(candles)
        if a is None:
            r.trade_allowed = False
            r.explanations.append("ATR unavailable: trading vetoed.")
            return r

        last = _c(candles[-1])
        r.atr14 = a
        r.atr_pct = (a / last * 100) if last else None

        if r.atr_pct is not None:
            if r.atr_pct < self.low_below:
                r.volatility_level = LOW
            elif r.atr_pct < self.high_above:
                r.volatility_level = NORMAL
            else:
                r.volatility_level = HIGH
            r.explanations.append(
                f"ATR14 {a:.5f} ({r.atr_pct:.3f}% of price): "
                f"{r.volatility_level} volatility.")

        last_range = _h(candles[-1]) - _l(candles[-1])
        if last_range > self.spike_factor * a:
            r.unusual_spike = True
            r.trade_allowed = False
            r.explanations.append(
                f"Last candle range {last_range:.5f} is unusually large "
                f"(>{self.spike_factor}x ATR): unstable, trading vetoed.")

        if not r.explanations or r.trade_allowed:
            r.trade_allowed = True
            r.explanations.append("Risk filters passed.")
        return r
