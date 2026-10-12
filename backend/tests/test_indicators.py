cat > backend/tests/test_indicators.py << 'PYEOF'
"""Tests for Agent 3 - Technical Indicators."""

from types import SimpleNamespace

from backend.agents.indicators import (
    IndicatorAgent,
    atr,
    macd,
    rsi,
    stochastic,
)


def _c(h, l, c, o=None):
    return SimpleNamespace(o=o if o is not None else c, h=h, l=l, c=c)


def test_rsi_rising_market():
    closes = [100 + i for i in range(30)]
    assert rsi(closes) == 100.0


def test_rsi_falling_market():
    closes = [100 - i for i in range(30)]
    assert rsi(closes) == 0.0


def test_rsi_flat_is_undefined_not_nan():
    assert rsi([50.0] * 30) is None


def test_rsi_insufficient_data():
    assert rsi([1.0] * 10) is None


def test_stochastic_close_at_high():
    candles = [_c(10, 0, 5) for _ in range(13)] + [_c(10, 0, 10) for _ in range(3)]
    k, d = stochastic(candles)
    assert k == 100.0
    assert d == 100.0


def test_stochastic_no_range_never_nan():
    candles = [_c(5, 5, 5) for _ in range(20)]
    k, d = stochastic(candles)
    assert k == 50.0 and d == 50.0


def test_stochastic_insufficient():
    assert stochastic([_c(1, 0, 1)] * 10) == (None, None)


def test_macd_flat_market():
    assert macd([5.0] * 40) == (0.0, 0.0, 0.0)


def test_macd_rising_market_positive():
    closes = [100 + 0.5 * i for i in range(60)]
    m, s, h = macd(closes)
    assert m > 0 and h > 0


def test_macd_insufficient():
    assert macd([1.0] * 20) is None


def test_atr_constant_range():
    candles = [_c(10, 8, 9) for _ in range(30)]
    assert atr(candles) == 2.0


def test_atr_insufficient():
    assert atr([_c(1, 0, 1)] * 10) is None


def test_agent_reports_with_little_data():
    candles = [_c(1, 0, 1)] * 5
    r = IndicatorAgent().analyze(candles, "EUR/USD", "M1")
    assert r.rsi14 is None and r.atr14 is None
    assert len(r.explanations) >= 3
PYEOF
