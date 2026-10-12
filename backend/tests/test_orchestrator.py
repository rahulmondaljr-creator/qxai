"""Tests for Orchestrator + Final Signal Validator."""

from types import SimpleNamespace

from backend.agents.risk import NO_TRADE
from backend.orchestrator import DOWN, UP, Orchestrator


def _c(o, h, l, c):
    return SimpleNamespace(o=o, h=h, l=l, c=c)


def _uptrend(n=20):
    candles = []
    for k in range(n):
        candles.append(_c(100 + 2 * k, 101 + 2 * k, 99 + 2 * k, 100.2 + 2 * k))
        candles.append(_c(103 + 2 * k, 104 + 2 * k, 102 + 2 * k, 103.5 + 2 * k))
    return candles


def _downtrend(n=20):
    candles = []
    for k in range(n):
        candles.append(_c(105 - 3 * k, 106 - 3 * k, 103 - 3 * k, 105.5 - 3 * k))
        candles.append(_c(101 - 3 * k, 102 - 3 * k, 99 - 3 * k, 101.5 - 3 * k))
    return candles


def _cs(candles, stale=False):
    return SimpleNamespace(completed=candles, stale=stale)


def test_stale_data_forces_no_trade():
    s = Orchestrator().analyze_candleset(_cs(_uptrend(), stale=True),
                                         "EUR/USD", "M1")
    assert s.decision == NO_TRADE
    assert s.data_freshness == "stale"


def test_risk_veto_forces_no_trade():
    s = Orchestrator().analyze_candleset(_cs(_uptrend()[:5]),
                                         "EUR/USD", "M1")
    assert s.decision == NO_TRADE
    assert s.risk_status == "vetoed"


def test_strong_uptrend_gives_up():
    candles = _uptrend()
    candles.append(_c(142, 141.8, 141, 141.8))   # small bearish
    candles.append(_c(141, 146, 143, 145.5))     # bullish engulfing + break
    s = Orchestrator().analyze_candleset(_cs(candles), "EUR/USD", "M1")
    assert s.decision == UP
    assert s.score >= 3


def test_strong_downtrend_gives_down():
    candles = _downtrend()
    candles.append(_c(46, 47, 45.2, 46))         # small bullish
    candles.append(_c(46, 46.5, 41, 42))         # bearish engulfing + break
    s = Orchestrator().analyze_candleset(_cs(candles), "EUR/USD", "M1")
    assert s.decision == DOWN
    assert s.score <= -3


def test_flat_market_gives_no_trade():
    candles = [_c(100, 100.5, 99.5, 100) for _ in range(40)]
    s = Orchestrator().analyze_candleset(_cs(candles), "EUR/USD", "M1")
    assert s.decision == NO_TRADE


def test_signal_dict_is_serialisable():
    s = Orchestrator().analyze_candleset(_cs(_uptrend()), "EUR/USD", "M1")
    d = s.to_dict()
    assert d["pair"] == "EUR/USD"
    assert d["decision"] in (UP, DOWN, NO_TRADE)
    assert isinstance(d["explanation"], list)
