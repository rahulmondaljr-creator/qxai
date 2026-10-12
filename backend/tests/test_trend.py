"""Tests for Agent 2 - Trend Analysis."""

from backend.agents.trend import (
    BEARISH,
    BULLISH,
    INSUFFICIENT,
    SIDEWAYS,
    Candle,
    TrendAgent,
    _ema,
    _swings,
)


def _candles(closes, start=1_700_000_000, step=60):
    out = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = prev
        out.append(Candle(time=start + i * step, open=o,
                          high=max(o, c), low=min(o, c), close=c))
        prev = c
    return out


def test_ema_constant_series():
    assert _ema([2.0] * 60, 20) == 2.0
    assert _ema([2.0] * 60, 50) == 2.0


def test_ema_known_values():
    values = [float(i) for i in range(1, 11)]
    assert _ema(values, 3) == 9.0


def test_ema_insufficient_data():
    assert _ema([1.0, 2.0], 20) is None


def test_bullish_trend():
    closes = [100 + i * 0.5 for i in range(80)]
    r = TrendAgent().analyze(_candles(closes), "USDJPY_otc", "M1")
    assert r.classification == BULLISH
    assert r.ema20 and r.ema50 and r.ema20 > r.ema50
    assert len(r.reasons) >= 2


def test_bearish_trend():
    closes = [200 - i * 0.5 for i in range(80)]
    r = TrendAgent().analyze(_candles(closes), "USDJPY_otc", "M1")
    assert r.classification == BEARISH
    assert r.ema20 < r.ema50


def test_sideways_flat_market():
    closes = [100.0 + (0.01 if i % 2 == 0 else -0.01) for i in range(80)]
    r = TrendAgent().analyze(_candles(closes), "USDJPY_otc", "M1")
    assert r.classification == SIDEWAYS


def test_insufficient_data():
    closes = [100 + i for i in range(10)]
    r = TrendAgent().analyze(_candles(closes), "EURUSD_otc", "M1")
    assert r.classification == INSUFFICIENT
    assert r.ema50 is None


def test_swing_detection():
    closes = [1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 2]
    candles = [Candle(time=i, open=c, high=c + 0.5, low=c - 0.5, close=c)
               for i, c in enumerate(closes)]
    highs, lows = _swings(candles, lookback=60)
    assert any(h > 5.0 for h in highs)
    assert len(lows) >= 1


def test_last_candle_never_swing():
    closes = [1, 2, 3, 4, 5, 6, 7]
    candles = [Candle(time=i, open=c, high=c, low=c, close=c)
               for i, c in enumerate(closes)]
    highs, _ = _swings(candles, 60)
    assert 7 not in highs  # forming candle must not be a swing
