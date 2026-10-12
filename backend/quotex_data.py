"""Agent 1 — Market Data. Fetch + normalize Quotex candles safely."""
import time
import asyncio
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional

log = logging.getLogger("qxai.data")

@dataclass
class Candle:
    t: int
    o: float
    h: float
    l: float
    c: float

@dataclass
class CandleSet:
    asset: str
    period: int
    completed: List[Candle]
    forming: Optional[Candle]
    issues: List[str]
    stale: bool
    newest_age_sec: float
    fetched_at: float
    def to_dict(self):
        return asdict(self)

def _to_candle(x) -> Optional[Candle]:
    try:
        return Candle(t=int(x["time"]), o=float(x["open"]), h=float(x["high"]),
                      l=float(x["low"]), c=float(x["close"]))
    except Exception:
        return None

def normalize_candles(raw, period_sec: int, now: Optional[int] = None):
    """Sort, dedupe, validate OHLC, detect gaps, split forming candle.
    Pure function — fully testable without network/pyquotex."""
    now = int(now if now is not None else time.time())
    issues: List[str] = []
    candles: List[Candle] = []
    seen = set()
    for x in raw or []:
        cd = _to_candle(x)
        if cd is None:
            issues.append("unparseable candle skipped")
            continue
        if cd.t in seen:
            issues.append(f"duplicate candle at t={cd.t} skipped")
            continue
        if cd.h < cd.l or cd.h < max(cd.o, cd.c) - 1e-12 or cd.l > min(cd.o, cd.c) + 1e-12:
            issues.append(f"invalid OHLC at t={cd.t} skipped")
            continue
        seen.add(cd.t)
        candles.append(cd)
    if any(candles[i].t > candles[i + 1].t for i in range(len(candles) - 1)):
        issues.append("out-of-order candles fixed by sorting")
        candles.sort(key=lambda c: c.t)
    for i in range(1, len(candles)):
        if candles[i].t - candles[i - 1].t > int(period_sec * 1.5):
            issues.append(f"missing candles between t={candles[i-1].t} and t={candles[i].t}")
    cur_start = (now // period_sec) * period_sec
    forming = None
    completed = candles
    if candles and candles[-1].t >= cur_start:
        forming = candles[-1]
        completed = candles[:-1]
    return completed, forming, issues

class RateLimiter:
    def __init__(self, min_interval: float = 1.2):
        self.min_interval = min_interval
        self._last = 0.0
    async def wait(self):
        dt = time.time() - self._last
        if dt < self.min_interval:
            await asyncio.sleep(self.min_interval - dt)
        self._last = time.time()

class QuotexData:
    """Lazy-imports pyquotex so tests and pure functions need neither."""
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.QX = None
        self.connected = False
        self._lock = asyncio.Lock()
        self._limiter = RateLimiter()

    async def connect(self, attempts: int = 5) -> bool:
        from pyquotex.stable_api import Quotex  # lazy import
        async with self._lock:
            if self.QX is not None:
                try:
                    if await self.QX.check_connect():
                        self.connected = True
                        return True
                except Exception:
                    pass
            for i in range(attempts):
                try:
                    self.QX = Quotex(email=self.email, password=self.password)
                    ok, msg = await self.QX.connect()
                    if ok:
                        self.connected = True
                        log.info("Quotex connected")
                        return True
                    log.warning("connect fail (%s): %s", i + 1, msg)
                except Exception as e:
                    log.warning("connect error (%s): %s", i + 1, e)
                await asyncio.sleep(4 + i * 2)
            self.connected = False
            return False

    async def get_candles(self, asset: str, period: int = 60, seconds: int = 21600,
                          max_attempts: int = 3) -> CandleSet:
        if not self.connected:
            if not await self.connect():
                raise RuntimeError("Quotex not connected")
        async with self._lock:
            raw = None
            last_err = None
            for a in range(max_attempts):
                try:
                    await self._limiter.wait()
                    raw = await self.QX.get_historical_candles(
                        asset, amount_of_seconds=seconds, period=period, max_workers=2)
                    if isinstance(raw, dict):
                        raw = raw.get("candles")
                    if raw:
                        break
                    last_err = RuntimeError("empty candle response")
                except Exception as e:
                    last_err = e
                    log.warning("candle fetch attempt %s failed for %s: %s", a + 1, asset, e)
                    await asyncio.sleep(2 + a)
            else:
                raise RuntimeError(f"could not fetch candles for {asset}: {last_err}")
        now = time.time()
        completed, forming, issues = normalize_candles(raw, period, now)
        newest = forming or (completed[-1] if completed else None)
        age = (now - newest.t) if newest else None
        stale = bool(age is not None and age > period * 3)
        if stale:
            issues.append(f"data stale: newest candle age {int(age)}s")
        return CandleSet(asset=asset, period=period, completed=completed, forming=forming,
                         issues=issues, stale=stale, newest_age_sec=round(age, 1) if age else -1,
                         fetched_at=now)
