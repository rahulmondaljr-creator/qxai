"""THE money demo: full pipeline -> UP / DOWN / NO_TRADE.

Run:  python -m backend.smoke_signal
"""

import asyncio
import json

from backend.config import settings
from backend.orchestrator import Orchestrator
from backend.quotex_data import QuotexData
from backend.watchlist import PAIRS, to_asset


async def main():
    pair = "USD/JPY"
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

    signal = Orchestrator().analyze_candleset(cs, pair, "M1")
    print(f"asset={used} completed={len(cs.completed)} "
          f"stale={cs.stale} issues={cs.issues}")
    print("=" * 40)
    print(f"DECISION: {signal.decision}   score={signal.score}")
    print(f"trend={signal.trend}  structure={signal.structure}  "
          f"risk={signal.risk_status}  data={signal.data_freshness}")
    print("-" * 40)
    print("Why:")
    for e in signal.explanation:
        print(" -", e)
    print("-" * 40)
    print("Full JSON:")
    print(json.dumps(signal.to_dict(), indent=1))


if __name__ == "__main__":
    asyncio.run(main())
