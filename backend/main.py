"""QXAI Analysis Backend — FastAPI entrypoint (Phase 9: live stream)."""

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config import settings
from backend.orchestrator import Orchestrator
from backend.quotex_data import QuotexData
from backend.scanner import TIMEFRAMES, Scanner

log = logging.getLogger("qxai")
logging.basicConfig(level=logging.INFO)

DATA: QuotexData | None = None
ORCH = Orchestrator()
SCANNER: Scanner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global DATA, SCANNER
    DATA = QuotexData(settings.qx_email, settings.qx_password)
    ok = await DATA.connect()
    log.info("startup: quotex connected=%s", ok)
    SCANNER = Scanner(DATA)
    SCANNER.start()
    log.info("auto-scan started: %s pairs x %s timeframes", 20, len(TIMEFRAMES))
    yield
    await SCANNER.stop()


app = FastAPI(title="QXAI Analysis Backend", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.frontend_origin.split(",")
                   if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

PAIR_RE = re.compile(r"^[A-Z0-9_]{3,15}$")


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"ready": bool(DATA is not None and DATA.connected)}


@app.get("/candles")
async def candles(
    pair: str = Query(..., description="e.g. EURUSD or EURUSD_otc"),
    period: int = Query(60, ge=1, le=86400),
    seconds: int = Query(21600, ge=300, le=7 * 86400),
):
    asset = pair.upper().replace("/", "")
    if not PAIR_RE.match(asset):
        raise HTTPException(400, "invalid pair format")
    if DATA is None:
        raise HTTPException(503, "backend starting")
    try:
        cs = await DATA.get_candles(asset, period=period, seconds=seconds)
    except Exception as e:
        log.warning("candles error: %s", e)
        raise HTTPException(502, str(e))
    return cs.to_dict()


@app.get("/api/signal")
async def signal(
    pair: str = Query(..., description="e.g. USDJPY or USD/JPY"),
    timeframe: str = Query("M1"),
):
    asset = pair.upper().replace("/", "")
    if not PAIR_RE.match(asset):
        raise HTTPException(400, "invalid pair format")
    if DATA is None:
        raise HTTPException(503, "backend starting")
    period = TIMEFRAMES.get(timeframe.upper(), 60)
    try:
        cs = await DATA.get_candles(asset, period=period, seconds=period * 360)
        sig = ORCH.analyze_candleset(cs, pair, timeframe.upper())
        d = sig.to_dict()
        last = cs.completed[-1] if cs.completed else None
        d["price"] = (float(getattr(last, "close", getattr(last, "c", 0)))
                      if last else None)
        d["entry_time"] = d["generated_at"]
        d["expiry_time"] = d["generated_at"] + period
    except Exception as e:
        log.warning("signal error: %s", e)
        raise HTTPException(502, str(e))
    return d


@app.get("/api/scan")
async def scan_status():
    if SCANNER is None:
        raise HTTPException(503, "scanner starting")
    return {"running": SCANNER.running, "last_cycle": SCANNER.last_cycle,
            "count": len(SCANNER.latest), "latest": list(SCANNER.latest.values())}


@app.get("/api/scan/signals")
async def scan_signals():
    if SCANNER is None:
        raise HTTPException(503, "scanner starting")
    return {"signals": SCANNER.signals}


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket, pair: str = "USDJPY", period: int = 60):
    """Live tick stream + payout, straight from Quotex to the browser."""
    await ws.accept()
    asset = pair.upper().replace("/", "")
    if DATA is None or getattr(DATA, "QX", None) is None:
        await ws.send_json({"type": "error", "msg": "backend starting"})
        await ws.close()
        return
    payout = None
    try:
        payout = await DATA.QX.get_payout(asset)
    except Exception:
        pass
    await ws.send_json({"type": "meta", "pair": pair, "payout": payout})
    try:
        await DATA.QX.start_candles_stream(asset, period)
        prev = None
        async for candle in DATA.QX.get_realtime_candles(asset, period):
            price = float(candle.get("close") or 0)
            await ws.send_json({
                "type": "tick",
                "t": candle.get("time"),
                "o": candle.get("open"), "h": candle.get("max"),
                "l": candle.get("min"), "c": price,
                "up": (prev is None or price >= prev),
            })
            prev = price
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("ws live error: %s", e)
    finally:
        try:
            await DATA.QX.stop_candles_stream(asset, period)
        except Exception:
            pass
