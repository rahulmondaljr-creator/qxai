"""Tests for Agent 6 - Volatility and Risk."""

from types import SimpleNamespace

from backend.agents.risk import HIGH, LOW, NORMAL, RiskAgent


def _c(h, l, c):
    return SimpleNamespace(h=h, l=l, c=c)


def _flat(rng, n=30, price=10000.0):
    return [_c(price + rng, price - rng, price) for _ in range(n)]


def test_low_volatility():
    r = RiskAgent().analyze(_flat(0.5), "EUR/USD", "M1")
    assert r.volatility_level == LOW
    assert r.trade_allowed and not r.unusual_spike


def test_normal_volatility():
    r = RiskAgent().analyze(_flat(3), "EUR/USD", "M1")
    assert r.volatility_level == NORMAL
    assert r.trade_allowed


def test_high_volatility():
    r = RiskAgent().analyze(_flat(20), "EUR/USD", "M1")
    assert r.volatility_level == HIGH
    assert r.trade_allowed  # high vol alone is not a veto


def test_spike_vetoes_trade():
    candles = _flat(1, n=29)
    candles.append(_c(10006, 9994, 10005))  # 12-wide vs ATR ~2
    r = RiskAgent().analyze(candles, "EUR/USD", "M1")
    assert r.unusual_spike
    assert not r.trade_allowed


def test_stale_data_vetoes_trade():
    r = RiskAgent().analyze(_flat(2), "EUR/USD", "M1", stale=True)
    assert not r.trade_allowed


def test_insufficient_data_vetoes_trade():
    r = RiskAgent().analyze(_flat(2, n=5), "EUR/USD", "M1")
    assert not r.trade_allowed
    assert r.atr14 is None


def test_tiny_input_never_crashes():
    r = RiskAgent().analyze([_c(1, 1, 1)], "EUR/USD", "M1")
    assert not r.trade_allowed
    assert r.explanations
