"""QXAI Analysis Backend — FastAPI entrypoint (Phase 7)."""

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config import settings
from backend.orchestrator import Orchestrator
from backend.quotex_data import QuotexData

log = logging.getLogger("qxai")
logging.basicConfig(level=logging.INFO)

DATA: QuotexData | None = None
ORCH = Orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global DATA
    DATA = QuotexData(settings.qx_email, settings.qx_password)
    ok = await DATA.connect()
    log.info("startup: quotex connected=%s", ok)
    yield


app = FastAPI(title="QXAI Analysis Backend", version="0.2.0",
              lifespan=lifespan)
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
    try:
        cs = await DATA.get_candles(asset, period=60, seconds=21600)
        sig = ORCH.analyze_candleset(cs, pair, timeframe)
    except Exception as e:
        log.warning("signal error: %s", e)
        raise HTTPException(502, str(e))
    return sig.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port)
