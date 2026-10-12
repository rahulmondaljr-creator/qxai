"""Debug: why does the strong-uptrend scenario score NO_TRADE?"""

from types import SimpleNamespace as N

from backend.agents.risk import RiskAgent
from backend.agents.trend import TrendAgent
from backend.agents.price_action import PriceActionAgent
from backend.agents.market_structure import MarketStructureAgent
from backend.orchestrator import Orchestrator, _to_candle


def c(o, h, l, cl):
    return N(o=o, h=h, l=l, c=cl)


raw = []
for k in range(20):
    raw.append(c(100 + 2 * k, 101 + 2 * k, 99 + 2 * k, 100.2 + 2 * k))
    raw.append(c(103 + 2 * k, 104 + 2 * k, 102 + 2 * k, 103.5 + 2 * k))
raw.append(c(142, 141.8, 141, 141.8))
raw.append(c(141, 146, 143, 145.5))

cs = [_to_candle(x) for x in raw]   # agents get normalised candles

t = TrendAgent().analyze(cs, "EUR/USD", "M1")
print("trend:", t.classification, t.ema20, t.ema50)

pa = PriceActionAgent().analyze(cs, "EUR/USD", "M1")
print("pa: engulf_bull=", pa.bullish_engulfing, "breakout=", pa.breakout)

st = MarketStructureAgent().analyze(cs, "EUR/USD", "M1")
print("structure:", st.structure, st.break_event,
      "hi=", len(st.swing_highs), "lo=", len(st.swing_lows))

r = RiskAgent().analyze(cs, "EUR/USD", "M1")
print("risk: allowed=", r.trade_allowed, "spike=", r.unusual_spike,
      "atr=", r.atr14, "atr_pct=", r.atr_pct)
for e in r.explanations:
    print("  *", e)

s = Orchestrator().analyze_candleset(N(completed=raw, stale=False),
                                     "EUR/USD", "M1")
print("SIGNAL:", s.decision, "score:", s.score)
for e in s.explanation:
    print(" -", e)
