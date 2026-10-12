"""Orchestrator + Agent 8 - Final Signal Validator (Phase 7).

Runs every agent on one CandleSet, then converts their outputs
into a decision: UP / DOWN / NO_TRADE, with reasons.
The score is rule-based, NOT a probability of winning.
"""

import time
from dataclasses import dataclass, field, asdict

from backend.agents.trend import BULLISH, BEARISH, TrendAgent
from backend.agents.indicators import IndicatorAgent
from backend.agents.price_action import (
    BREAKOUT_DOWN, BREAKOUT_UP, PriceActionAgent)
from backend.agents.market_structure import (
    BEAR_BREAK, BULL_BREAK, DOWNTREND, UPTREND, MarketStructureAgent)
from backend.agents.risk import NO_TRADE, RiskAgent

UP = "UP"
DOWN = "DOWN"
STRATEGY_VERSION = "orchestrator-7.0.0"


@dataclass
class Signal:
    pair: str
    timeframe: str
    generated_at: float
    data_freshness: str
    trend: str
    trend_reasons: list
    indicator_summary: list
    price_action_summary: list
    structure: str
    risk_status: str
    score: int
    decision: str
    explanation: list
    strategy_version: str = STRATEGY_VERSION

    def to_dict(self):
        return asdict(self)


class FinalSignalValidator:
    def __init__(self, up_threshold: int = 3, down_threshold: int = -3):
        self.up_threshold = up_threshold
        self.down_threshold = down_threshold

    def decide(self, trend, indicators, price_action, structure,
               risk, freshness):
        explanation = []
        score = 0

        if freshness == "stale":
            explanation.append("Data is stale: no signal on delayed data.")
            return NO_TRADE, score, explanation
        if not risk.trade_allowed:
            explanation.append("Risk veto: " + " | ".join(risk.explanations))
            return NO_TRADE, score, explanation
        if trend.ema50 is None:
            explanation.append("Insufficient candle history for trend.")
            return NO_TRADE, score, explanation

        if trend.classification == BULLISH:
            score += 2
            explanation.append("Trend bullish (+2).")
        elif trend.classification == BEARISH:
            score -= 2
            explanation.append("Trend bearish (-2).")

        if indicators.rsi14 is not None:
            if indicators.rsi14 >= 70:
                score -= 1
                explanation.append(f"RSI {indicators.rsi14:.0f} overbought (-1).")
            elif indicators.rsi14 <= 30:
                score += 1
                explanation.append(f"RSI {indicators.rsi14:.0f} oversold (+1).")
        if indicators.macd_hist is not None:
            if indicators.macd_hist >= 0:
                score += 1
                explanation.append("MACD histogram positive (+1).")
            else:
                score -= 1
                explanation.append("MACD histogram negative (-1).")

        if price_action.bullish_engulfing or price_action.bullish_pin:
            score += 1
            explanation.append("Bullish price-action pattern (+1).")
        if price_action.bearish_engulfing or price_action.bearish_pin:
            score -= 1
            explanation.append("Bearish price-action pattern (-1).")
        if price_action.breakout == BREAKOUT_UP:
            score += 1
            explanation.append("Upside breakout watch (+1).")
        elif price_action.breakout == BREAKOUT_DOWN:
            score -= 1
            explanation.append("Downside breakout watch (-1).")

        if structure.structure == UPTREND:
            score += 1
            explanation.append("Market structure uptrend (+1).")
        elif structure.structure == DOWNTREND:
            score -= 1
            explanation.append("Market structure downtrend (-1).")
        if structure.break_event == BULL_BREAK:
            score += 1
            explanation.append("Bullish structure break (+1).")
        elif structure.break_event == BEAR_BREAK:
            score -= 1
            explanation.append("Bearish structure break (-1).")

        if score >= self.up_threshold:
            decision = UP
        elif score <= self.down_threshold:
            decision = DOWN
        else:
            decision = NO_TRADE
            explanation.append(
                f"Score {score} below conviction thresholds: stand aside.")
        return decision, score, explanation


class Orchestrator:
    """Runs all agents on one CandleSet and emits the final Signal."""

    def __init__(self):
        self.trend_agent = TrendAgent()
        self.indicator_agent = IndicatorAgent()
        self.price_action_agent = PriceActionAgent()
        self.structure_agent = MarketStructureAgent()
        self.risk_agent = RiskAgent()
        self.validator = FinalSignalValidator()

    def analyze_candleset(self, cs, pair: str, timeframe: str) -> Signal:
        candles = list(cs.completed)
        freshness = "stale" if cs.stale else "fresh"

        trend = self.trend_agent.analyze(candles, pair, timeframe)
        indicators = self.indicator_agent.analyze(candles, pair, timeframe)
        price_action = self.price_action_agent.analyze(candles, pair, timeframe)
        structure = self.structure_agent.analyze(candles, pair, timeframe)
        risk = self.risk_agent.analyze(candles, pair, timeframe,
                                       stale=cs.stale)
        decision, score, explanation = self.validator.decide(
            trend, indicators, price_action, structure, risk, freshness)

        return Signal(
            pair=pair, timeframe=timeframe, generated_at=time.time(),
            data_freshness=freshness, trend=trend.classification,
            trend_reasons=trend.reasons,
            indicator_summary=indicators.explanations,
            price_action_summary=price_action.explanations,
            structure=structure.structure,
            risk_status="allowed" if risk.trade_allowed else "vetoed",
            score=score, decision=decision, explanation=explanation,
        )
