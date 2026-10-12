"""Auto-scan service: round-robin analysis of all watchlist pairs/timeframes.

Scans every (pair, timeframe) combination continuously and keeps the
latest result in memory. Non-NO_TRADE decisions are pushed to a
signal history. Conservative pacing avoids rate-limit bans.
"""

import asyncio
import logging
import time

from backend.orchestrator import Orchestrator
from backend.watchlist import PAIRS

log = logging.getLogger("qxai.scan")

TIMEFRAMES = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800}


class Scanner:
    def __init__(self, data, interval_between_items: float = 2.0):
        self.data = data
        self.orch = Orchestrator()
        self.interval = interval_between_items
        self.latest = {}      # (pair, tf) -> signal dict
        self.signals = []     # non-NO_TRADE history, newest first
        self.running = False
        self._task = None
        self.last_cycle = 0.0

    def start(self):
        if self._task is None:
            self.running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        while self.running:
            self.last_cycle = time.time()
            for pair in PAIRS:
                for tf, period in TIMEFRAMES.items():
                    if not self.running:
                        return
                    try:
                        await self._scan_item(pair, tf, period)
                    except Exception as e:
                        log.warning("scan %s %s failed: %s", pair, tf, e)
                    await asyncio.sleep(self.interval)
            await asyncio.sleep(5)

    async def _scan_item(self, pair: str, tf: str, period: int):
        cs = await self.data.get_candles(
            pair.replace("/", ""), period=period, seconds=period * 360)
        sig = self.orch.analyze_candleset(cs, pair, tf)
        d = sig.to_dict()
        last = cs.completed[-1] if cs.completed else None
        price = (float(getattr(last, "close", getattr(last, "c", 0)))
                 if last else None)
        d["price"] = price
        d["entry_time"] = d["generated_at"]
        d["expiry_time"] = d["generated_at"] + period
        self.latest[(pair, tf)] = d
        if d["decision"] != "NO_TRADE":
            self.signals.insert(0, d)
            del self.signals[100:]
            log.info("SIGNAL %s %s %s score=%s",
                     pair, tf, d["decision"], d["score"])
