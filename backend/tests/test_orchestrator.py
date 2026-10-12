"""Tests for Orchestrator + Final Signal Validator."""

from types import SimpleNamespace

from backend.agents.risk import NO_TRADE
from backend.orchestrator import DOWN, UP, Orchestrator


def _c(o, h, l, c):
    return SimpleNamespace(o=o, h=h, l=l, c=c)


def _uptrend(n=26):
    candles = []
    for k in range(n):
        candles.append(_c(100 + 2 * k, 101 + 2 * k, 99 + 2 * k, 100.2 + 2 * k))
        candles.append(_c(103 + 2 * k, 104 + 2 * k, 102 + 2 * k, 103.5 + 2 * k))
    return candles


def _downtrend(n=26):
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
    top = candles[-1].c
    candles.append(_c(top + 0.5, top + 0.3, top - 0.2, top + 0.3))
    candles.append(_c(top - 0.5, top + 5, top + 2, top + 4.5))
    s = Orchestrator().analyze_candleset(_cs(candles), "EUR/USD", "M1")
    assert s.decision == UP
    assert s.score >= 3


def test_strong_downtrend_gives_down():
    candles = _downtrend()
    bot = candles[-1].c
    candles.append(_c(bot - 0.5, bot + 0.2, bot - 0.3, bot - 0.2))
    candles.append(_c(bot + 0.5, bot + 1, bot - 5, bot - 4.5))
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
