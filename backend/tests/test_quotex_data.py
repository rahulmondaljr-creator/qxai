import time
import asyncio
from backend.quotex_data import normalize_candles, QuotexData

def mk(t, o=1.0, h=1.1, l=0.9, c=1.05):
    return {"time": t, "open": o, "high": h, "low": l, "close": c}

def test_sorts_and_dedupes():
    now = 1_000_000
    raw = [mk(now - 120), mk(now - 180), mk(now - 180), mk(now - 60)]
    comp, forming, issues = normalize_candles(raw, 60, now)
    ts = [c.t for c in comp] + ([forming.t] if forming else [])
    assert ts == sorted(set(ts))
    assert any("duplicate" in i for i in issues)
    assert any("out-of-order" in i for i in issues)

def test_gap_detected_not_silently_filled():
    now = 1_000_000
    raw = [mk(now - 600), mk(now - 60)]
    comp, forming, issues = normalize_candles(raw, 60, now)
    assert any("missing candles" in i for i in issues)

def test_forming_candle_split():
    now = 1_000_000
    cur = (now // 60) * 60
    raw = [mk(cur - 120), mk(cur - 60), mk(cur)]
    comp, forming, issues = normalize_candles(raw, 60, now)
    assert forming is not None and forming.t == cur
    assert all(c.t < cur for c in comp)

def test_invalid_ohlc_skipped():
    now = 1_000_000
    raw = [mk(now - 60, o=1.0, h=0.5, l=0.9, c=1.05), mk(now - 120)]
    comp, forming, issues = normalize_candles(raw, 60, now)
    assert any("invalid OHLC" in i for i in issues)

class FakeQX:
    async def get_historical_candles(self, asset, amount_of_seconds, period, max_workers):
        now = int(time.time())
        cur = (now // period) * period
        return [mk(cur - 3600), mk(cur - 3540), mk(cur - 3480)]

def test_adapter_flags_stale_data():
    async def run():
        d = QuotexData("e@x.com", "pw")
        d.QX = FakeQX()
        d.connected = True
        cs = await d.get_candles("EURUSD", period=60, seconds=3600)
        assert cs.stale is True
        assert any("stale" in i for i in cs.issues)
        assert cs.completed and cs.completed[0].t < cs.completed[-1].t
    asyncio.run(run())

class FreshQX:
    async def get_historical_candles(self, asset, amount_of_seconds, period, max_workers):
        now = int(time.time())
        cur = (now // period) * period
        return [mk(cur - 120), mk(cur - 60), mk(cur)]

def test_adapter_fresh_data_not_stale():
    async def run():
        d = QuotexData("e@x.com", "pw")
        d.QX = FreshQX()
        d.connected = True
        cs = await d.get_candles("EURUSD", period=60, seconds=3600)
        assert cs.stale is False
        assert cs.forming is not None
        assert len(cs.completed) == 2
    asyncio.run(run())
