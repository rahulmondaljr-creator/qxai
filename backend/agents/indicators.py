cat > backend/agents/indicators.py << 'PYEOF'
"""Agent 3 - Technical Indicator Agent (Phase 3).

RSI(14), Stochastic, MACD, ATR - pure standard library.
Insufficient history returns None (never NaN, never invented data).
Indicators describe conditions; they do not guarantee outcomes.
"""

from dataclasses import dataclass, field

STRATEGY_VERSION = "indicator-agent-3.0.1"


def _ohlc(c, long: str, short: str) -> float:
    v = getattr(c, long, None)
    return float(v if v is not None else getattr(c, short))


def _close(c) -> float:
    return _ohlc(c, "close", "c")


def _high(c) -> float:
    return _ohlc(c, "high", "h")


def _low(c) -> float:
    return _ohlc(c, "low", "l")


def _ema_series(values: list[float], period: int) -> list[float]:
    k = 2 / (period + 1)
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's RSI. None if undefined (flat market) or insufficient data."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else None
    return 100 - 100 / (1 + avg_gain / avg_loss)


def stochastic(candles, k_period: int = 14, d_period: int = 3):
    """Returns (stoch_k, stoch_d); None pair if insufficient data."""
    if len(candles) < k_period + d_period - 1:
        return None, None
    ks = []
    for i in range(len(candles) - d_period, len(candles)):
        window = candles[i - k_period + 1: i + 1]
        hh = max(_high(c) for c in window)
        ll = min(_low(c) for c in window)
        rng = hh - ll
        ks.append(50.0 if rng == 0 else (_close(candles[i]) - ll) / rng * 100)
    return ks[-1], sum(ks) / len(ks)


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, macd_signal, macd_hist) or None if too short.

    Both EMAs are aligned to the SAME candle index before subtraction;
    the slow EMA (later seed) anchors the alignment.
    """
    if len(closes) < slow + signal - 1:
        return None
    ef = _ema_series(closes, fast)
    es = _ema_series(closes, slow)
    line = []
    for j in range(len(es)):
        idx = slow - 1 + j
        line.append(ef[idx - fast + 1] - es[j])
    sig = _ema_series(line, signal)
    m = line[-1]
    s = sig[-1]
    return m, s, m - s


def atr(candles, period: int = 14) -> float | None:
    """Wilder's ATR from true ranges. None if insufficient data."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = _high(candles[i]), _low(candles[i]), _close(candles[i - 1])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return a


@dataclass
class IndicatorResult:
    pair: str
    timeframe: str
    rsi14: float | None
    stoch_k: float | None
    stoch_d: float | None
    macd_line: float | None
    macd_signal: float | None
    macd_hist: float | None
    atr14: float | None
    explanations: list[str] = field(default_factory=list)
    strategy_version: str = STRATEGY_VERSION


class IndicatorAgent:
    def analyze(self, candles, pair: str, timeframe: str) -> IndicatorResult:
        closes = [_close(c) for c in candles]
        r = IndicatorResult(pair, timeframe, None, None, None,
                            None, None, None, None, [])

        r.rsi14 = rsi(closes)
        if r.rsi14 is None:
            r.explanations.append("RSI14 unavailable: need at least 15 closes.")
        elif r.rsi14 >= 70:
            r.explanations.append(
                f"RSI14 {r.rsi14:.1f}: overbought zone (not a guaranteed reversal).")
        elif r.rsi14 <= 30:
            r.explanations.append(
                f"RSI14 {r.rsi14:.1f}: oversold zone (not a guaranteed reversal).")
        else:
            r.explanations.append(f"RSI14 {r.rsi14:.1f}: neutral zone (30-70).")

        r.stoch_k, r.stoch_d = stochastic(candles)
        if r.stoch_k is None:
            r.explanations.append("Stochastic unavailable: need at least 16 candles.")
        else:
            r.explanations.append(
                f"Stochastic %K {r.stoch_k:.1f}, %D {r.stoch_d:.1f} (0-100 scale).")

        m = macd(closes)
        if m is None:
            r.explanations.append("MACD unavailable: need at least 34 closes.")
        else:
            r.macd_line, r.macd_signal, r.macd_hist = m
            side = "above" if r.macd_hist >= 0 else "below"
            r.explanations.append(
                f"MACD line {r.macd_line:.6f} is {side} signal {r.macd_signal:.6f}.")

        r.atr14 = atr(candles)
        if r.atr14 is None:
            r.explanations.append("ATR14 unavailable: need at least 15 candles.")
        else:
            last = closes[-1] if closes else 0.0
            pct = (r.atr14 / last * 100) if last else 0.0
            r.explanations.append(
                f"ATR14 {r.atr14:.5f} (~{pct:.2f}% of price): volatility measure.")
        return r
PYEOF
