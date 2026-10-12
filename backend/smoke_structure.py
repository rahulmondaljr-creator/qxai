"""Live smoke test: watchlist pair -> MarketStructureAgent.

Run:  python -m backend.smoke_structure
"""

import asyncio

from backend.agents.market_structure import MarketStructureAgent
from backend.config import settings
from backend.quotex_data import QuotexData
from backend.watchlist import PAIRS, to_asset


async def main():
    pair = PAIRS[6]  # GBP/USD
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
    r = MarketStructureAgent().analyze(cs.completed, pair, "M1")
    print(f"structure={r.structure} break={r.break_event}")
    print(f"swing_highs={len(r.swing_highs)} swing_lows={len(r.swing_lows)}")
    for z in r.support_zones:
        print(f"support {z['low']:.5f}-{z['high']:.5f} "
              f"center={z['center']:.5f} touches={z['touches']}")
    for z in r.resistance_zones:
        print(f"resistance {z['low']:.5f}-{z['high']:.5f} "
              f"center={z['center']:.5f} touches={z['touches']}")
    for e in r.explanations:
        print(" -", e)


if __name__ == "__main__":
    asyncio.run(main())
