from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MarketData(BaseModel):
    symbol: str = "BTCUSDT"
    current_price: float = 0.0
    volatility_index: float = 0.0
    liquidity_m2: float = 0.0


class RegimeState(BaseModel):
    primary_regime: str = "unknown"
    secondary_regime: str = "unknown"
    divine_distance: float = 1.0


class RiskMetrics(BaseModel):
    current_drawdown: float = 0.0
    max_drawdown_limit: float = -0.22
    daily_loss: float = 0.0
    is_safe: bool = True


class DecisionRecord(BaseModel):
    timestamp: str
    bot_name: str
    action: str
    reasoning: str


class IncidentRecord(BaseModel):
    timestamp: str
    source: str
    severity: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class MKMGlobalState(BaseModel):
    run_id: str
    timestamp: str
    market: MarketData = Field(default_factory=MarketData)
    regime: RegimeState = Field(default_factory=RegimeState)
    risk: RiskMetrics = Field(default_factory=RiskMetrics)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    incidents: list[IncidentRecord] = Field(default_factory=list)
    sentinel_approval: bool = True
    sentinel_message: str = "ok"
    execution_mode: str = "read-only"


def default_state(run_id: str | None = None, execution_mode: str = "read-only") -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    state = MKMGlobalState(
        run_id=run_id or f"run-{int(datetime.utcnow().timestamp())}",
        timestamp=now,
        execution_mode=execution_mode,
    )
    return state.model_dump(mode="json")
