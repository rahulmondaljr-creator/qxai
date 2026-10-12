"""Live smoke test: watchlist pair -> IndicatorAgent.

Run:  python -m backend.smoke_indicators
"""

import asyncio

from backend.agents.indicators import IndicatorAgent
from backend.config import settings
from backend.quotex_data import QuotexData
from backend.watchlist import PAIRS, to_asset


async def main():
    pair = PAIRS[1]  # EUR/USD
    data = QuotexData(settings.qx_email, settings.qx_password)
    if not await data.connect():
        print("CONNECT FAILED")
        return
    cs, used = None, None
    for asset in (to_asset(pair), pair):
        try:
            cs = await data.get_candles(asset, period=60, seconds=21600)
        except Exception as e:
            print(f"{asset}: fetch error {e}")
            continue
        if cs.completed:
            used = asset
            break
    if not cs or not cs.completed:
        print("NO CANDLES: market closed or unknown pair code")
        return
    print(f"asset={used} completed={len(cs.completed)} "
          f"stale={cs.stale} issues={cs.issues}")
    r = IndicatorAgent().analyze(cs.completed, pair, "M1")
    print(f"rsi14={r.rsi14}")
    print(f"stoch_k={r.stoch_k} stoch_d={r.stoch_d}")
    print(f"macd_line={r.macd_line} macd_signal={r.macd_signal} "
          f"macd_hist={r.macd_hist}")
    print(f"atr14={r.atr14}")
    for e in r.explanations:
        print(" -", e)


if __name__ == "__main__":
    asyncio.run(main())
