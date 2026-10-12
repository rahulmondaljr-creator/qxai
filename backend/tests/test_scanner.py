"""Tests for the auto-scan service (no network)."""

from types import SimpleNamespace

import pytest

from backend.orchestrator import UP
from backend.scanner import TIMEFRAMES, Scanner


def _c(o, h, l, c):
    return SimpleNamespace(o=o, h=h, l=l, c=c)


def _uptrend(n=26):
    candles = []
    for k in range(n):
        candles.append(_c(100 + 2 * k, 101 + 2 * k, 99 + 2 * k, 100.2 + 2 * k))
        candles.append(_c(103 + 2 * k, 104 + 2 * k, 102 + 2 * k, 103.5 + 2 * k))
    return candles


class FakeData:
    def __init__(self, candles):
        self.candles = candles

    async def get_candles(self, asset, period=60, seconds=21600):
        return SimpleNamespace(completed=list(self.candles), stale=False)


def test_timeframes_cover_four_charts():
    assert TIMEFRAMES == {"M1": 60, "M5": 300, "M15": 900, "M30": 1800}


@pytest.mark.asyncio
async def test_scanner_records_signal_with_price_and_expiry():
    candles = _uptrend()
    top = candles[-1].c
    candles.append(_c(top + 0.5, top + 0.3, top - 0.2, top + 0.3))
    candles.append(_c(top - 0.5, top + 5, top + 2, top + 4.5))
    scanner = Scanner(FakeData(candles), interval_between_items=0)
    await scanner._scan_item("EUR/USD", "M5", 300)
    entry = scanner.latest[("EUR/USD", "M5")]
    assert entry["decision"] == UP
    assert entry["price"] and entry["price"] > 0
    assert entry["expiry_time"] - entry["entry_time"] == 300
    assert scanner.signals and scanner.signals[0]["pair"] == "EUR/USD"
