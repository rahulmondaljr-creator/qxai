"""Live smoke test: watchlist pair -> PriceActionAgent.

Run:  python -m backend.smoke_price_action
"""

import asyncio

from backend.agents.price_action import PriceActionAgent
from backend.config import settings
from backend.quotex_data import QuotexData
from backend.watchlist import PAIRS, to_asset


async def main():
    pair = PAIRS[0]  # EUR/JPY
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
    r = PriceActionAgent().analyze(cs.completed, pair, "M1")
    print(f"bull_engulf={r.bullish_engulfing} bear_engulf={r.bearish_engulfing}")
    print(f"bull_pin={r.bullish_pin} bear_pin={r.bearish_pin}")
    print(f"strength={r.strength:.3f} breakout={r.breakout}")
    for e in r.explanations:
        print(" -", e)


if __name__ == "__main__":
    asyncio.run(main())
