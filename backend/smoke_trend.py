"""Live smoke test: real Quotex candles -> TrendAgent.

Run:  python -m backend.smoke_trend
"""

import asyncio

from backend.config import settings
from backend.quotex_data import QuotexData
from backend.agents.trend import Candle, TrendAgent


def to_trend_candle(c):
    """Adapt adapter candles (object or dict) to trend.Candle."""
    if isinstance(c, dict):
        return Candle(time=int(c.get("time", c.get("t", 0))),
                      open=float(c["open"]), high=float(c["high"]),
                      low=float(c["low"]), close=float(c["close"]))
    return Candle(time=int(getattr(c, "t", getattr(c, "time", 0))),
                  open=float(getattr(c, "open")),
                  high=float(getattr(c, "high")),
                  low=float(getattr(c, "low")),
                  close=float(getattr(c, "close")))


async def main():
    pair = "USDJPY_otc"
    data = QuotexData(settings.qx_email, settings.qx_password)
    if not await data.connect():
        print("CONNECT FAILED")
        return
    cs = await data.get_candles(pair, period=60, seconds=21600)
    candles = [to_trend_candle(c) for c in cs.completed]
    print(f"pair={pair} completed={len(candles)} "
          f"stale={cs.stale} issues={cs.issues}")
    if len(candles) < 50:
        print("NOT ENOUGH CANDLES FOR EMA50")
        return
    r = TrendAgent().analyze(candles, pair, "M1")
    print("classification:", r.classification)
    print(f"ema20={r.ema20:.5f} ema50={r.ema50:.5f}")
    for reason in r.reasons:
        print(" -", reason)


if __name__ == "__main__":
    asyncio.run(main())
