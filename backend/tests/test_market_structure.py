"""Tests for Agent 5 - Market Structure."""

from types import SimpleNamespace

from backend.agents.market_structure import (
    BEAR_BREAK,
    BULL_BREAK,
    DOWNTREND,
    NO_BREAK,
    UPTREND,
    MarketStructureAgent,
    cluster_zones,
    find_swings,
)


def _c(h, l, c):
    return SimpleNamespace(h=h, l=l, c=c)


def _uptrend_zigzag(n=8):
    """Realistic ascent: trough, peak, higher trough, higher peak..."""
    candles = []
    for k in range(n):
        candles.append(_c(101 + 2 * k, 99 + 2 * k, 100 + 2 * k))  # trough
        candles.append(_c(104 + 2 * k, 102 + 2 * k, 103 + 2 * k))  # peak
    return candles


def _downtrend_zigzag(n=8):
    """Realistic descent: peak, trough, lower peak, lower trough..."""
    candles = []
    for k in range(n):
        candles.append(_c(106 - 3 * k, 103 - 3 * k, 105 - 3 * k))  # peak
        candles.append(_c(102 - 3 * k, 99 - 3 * k, 101 - 3 * k))   # trough
    return candles


def test_find_swings_detects_peak_and_trough():
    closes = [1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 2]
    candles = [_c(x + 0.5, x - 0.5, x) for x in closes]
    highs, lows = find_swings(candles, 60)
    assert any(h >= 5.0 for h in highs)
    assert any(lv <= 1.0 for lv in lows)


def test_last_candle_never_a_swing():
    candles = [_c(i + 1, i - 1, i) for i in range(2, 10)]
    highs, _ = find_swings(candles, 60)
    assert 9 not in highs  # forming candle excluded


def test_cluster_zones_group_nearby_levels():
    zones = cluster_zones([10.0, 10.01, 10.005, 12.0], tolerance=0.05)
    assert len(zones) == 2
    assert zones[0]["touches"] == 3
    assert zones[1]["center"] == 12.0


def test_structure_uptrend():
    r = MarketStructureAgent().analyze(_uptrend_zigzag(), "EUR/USD", "M1")
    assert r.structure == UPTREND


def test_structure_downtrend():
    r = MarketStructureAgent().analyze(_downtrend_zigzag(), "EUR/USD", "M1")
    assert r.structure == DOWNTREND


def test_bullish_structure_break():
    candles = _uptrend_zigzag()
    candles += [_c(115, 115, 115) for _ in range(3)]
    candles.append(_c(120, 118.5, 119.5))  # closes above last swing high
    r = MarketStructureAgent().analyze(candles, "EUR/USD", "M1")
    assert r.break_event == BULL_BREAK


def test_no_break_inside_range():
    candles = [_c(10, 8, 9) for _ in range(25)]
    r = MarketStructureAgent().analyze(candles, "EUR/USD", "M1")
    assert r.break_event == NO_BREAK


def test_tiny_input_never_crashes():
    r = MarketStructureAgent().analyze([_c(1, 1, 1)], "EUR/USD", "M1")
    assert r.explanations
    assert r.break_event == NO_BREAK
