"""Tests for Agent 4 - Price Action."""

from types import SimpleNamespace

from backend.agents.price_action import (
    BREAKOUT_DOWN,
    BREAKOUT_NONE,
    BREAKOUT_UP,
    PriceActionAgent,
    candle_strength,
    detect_breakout,
    is_bearish_engulfing,
    is_bearish_pin,
    is_bullish_engulfing,
    is_bullish_pin,
)


def _c(o, h, l, c):
    return SimpleNamespace(o=o, h=h, l=l, c=c)


def test_bullish_engulfing():
    prev = _c(10, 10.5, 9.5, 9)     # bearish
    cur = _c(8.5, 11, 8, 10.5)      # bullish, engulfs prev body
    assert is_bullish_engulfing(prev, cur)
    assert not is_bearish_engulfing(prev, cur)


def test_bearish_engulfing():
    prev = _c(9, 10.5, 8.8, 10)     # bullish
    cur = _c(10.5, 10.8, 8.5, 8.8)  # bearish, engulfs prev body
    assert is_bearish_engulfing(prev, cur)
    assert not is_bullish_engulfing(prev, cur)


def test_no_engulfing_same_direction():
    prev = _c(9, 10, 8.8, 9.8)
    cur = _c(9.9, 11, 9.8, 10.8)
    assert not is_bullish_engulfing(prev, cur)
    assert not is_bearish_engulfing(prev, cur)


def test_bullish_pin_bar():
    c = _c(10, 10.3, 8.0, 10.2)     # long lower wick, close near high
    assert is_bullish_pin(c)
    assert not is_bearish_pin(c)


def test_bearish_pin_bar():
    c = _c(10, 12.0, 9.7, 9.8)      # long upper wick, close near low
    assert is_bearish_pin(c)
    assert not is_bullish_pin(c)


def test_doji_is_not_a_pin():
    c = _c(10, 10.5, 9.5, 10)       # zero body -> no pin, no crash
    assert not is_bullish_pin(c)
    assert not is_bearish_pin(c)


def test_candle_strength_extremes():
    assert candle_strength(_c(9, 11, 9, 11)) == 1.0
    assert candle_strength(_c(9, 11, 9, 9)) == -1.0
    assert abs(candle_strength(_c(9, 11, 9, 10))) < 1e-9
    assert candle_strength(_c(5, 5, 5, 5)) == 0.0


def test_breakout_up():
    candles = [_c(9, 10, 8.5, 9.5) for _ in range(25)]
    candles.append(_c(10.2, 10.6, 10.1, 10.5))
    assert detect_breakout(candles) == BREAKOUT_UP


def test_breakout_down():
    candles = [_c(9, 10, 8.5, 9.5) for _ in range(25)]
    candles.append(_c(8.4, 8.6, 8.0, 8.1))
    assert detect_breakout(candles) == BREAKOUT_DOWN


def test_no_breakout_insufficient():
    candles = [_c(9, 10, 8.5, 9.5) for _ in range(10)]
    assert detect_breakout(candles) == BREAKOUT_NONE


def test_agent_never_crashes_on_tiny_input():
    r = PriceActionAgent().analyze([_c(1, 1, 1, 1)], "EUR/USD", "M1")
    assert r.explanations
    assert r.breakout == BREAKOUT_NONE
