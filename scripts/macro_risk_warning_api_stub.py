# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.8, M:0.4}
# Balance: 89
# Purpose: Track C Macro Risk Warning API stub endpoint implementation.
# Keywords: FastAPI, API, risk warning, Track C, endpoint
#!/usr/bin/env python3
"""FastAPI stub for Track C Macro Risk Warning API.

Run:
  uvicorn scripts.macro_risk_warning_api_stub:app --host 127.0.0.1 --port 8020
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PACK = ROOT / "docs" / "final" / "artifacts" / "track_c_evidence_pack_latest.json"
EVIDENCE_ARTIFACT = ROOT / "docs" / "final" / "artifacts" / "integrated_governance_v1_latest.json"

DecisionState = Literal["GO", "WATCH", "HOLD", "FORCE_HOLD", "REDUCE_EXPOSURE"]
RiskWarningLevel = Literal["normal", "elevated", "high", "critical"]
ConfidenceBand = Literal["low", "medium", "high"]
Posture = Literal["maintain", "watch_tighten", "reduce_exposure", "halt_new_entries"]


class MacroRiskWarningRequest(BaseModel):
    client_request_id: str
    asset_scope: str
    horizon: Literal["1h", "4h", "24h", "7d"] = "24h"
    include_evidence_ref: bool = False


class Insight7(BaseModel):
    market_liquidity_stress: float = Field(ge=0.0, le=1.0)
    cross_asset_dislocation: float = Field(ge=0.0, le=1.0)
    crowd_positioning_fragility: float = Field(ge=0.0, le=1.0)
    volatility_regime_shift: float = Field(ge=0.0, le=1.0)
    funding_pressure_signal: float = Field(ge=0.0, le=1.0)
    macro_policy_shock_risk: float = Field(ge=0.0, le=1.0)
    tail_event_pressure: float = Field(ge=0.0, le=1.0)


class RegimeContext(BaseModel):
    primary_regime_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    secondary_regime_notes: list[str] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    artifact_path: str
    artifact_hash_sha256: str


class Disclaimer(BaseModel):
    not_investment_advice: bool = True
    no_buy_sell_instruction: bool = True
    no_return_guarantee: bool = True
    final_decision_with_operator: bool = True


class MacroRiskWarningResponse(BaseModel):
    api_contract_version: str = "1.0.0"
    schema_version: str = "macro_risk_warning_api_response_contract_v1"
    request_id: str
    timestamp_utc: str
    asset_scope: str
    decision_state: DecisionState
    risk_warning_level: RiskWarningLevel
    confidence_band: ConfidenceBand
    insight_7: Insight7
    regime_context: RegimeContext
    recommended_operator_posture: Posture
    evidence_ref: EvidenceRef | None = None
    ttl_seconds: int = 900
    disclaimer: Disclaimer = Field(default_factory=Disclaimer)


app = FastAPI(title="MKM Macro Risk Warning API Stub", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_governance_score() -> float:
    if not EVIDENCE_PACK.is_file():
        return 0.35
    try:
        doc = json.loads(EVIDENCE_PACK.read_text(encoding="utf-8"))
        return float((doc.get("governance") or {}).get("final_score", 0.35))
    except Exception:
        return 0.35


def _artifact_hash(path: Path) -> str:
    if not path.is_file():
        return "UNAVAILABLE_ARTIFACT_HASH"
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_macro_risk_warning_response(req: MacroRiskWarningRequest) -> MacroRiskWarningResponse:
    score = _load_governance_score()
    if score >= 0.75:
        state: DecisionState = "FORCE_HOLD"
        level: RiskWarningLevel = "critical"
        confidence: ConfidenceBand = "high"
        posture: Posture = "halt_new_entries"
        regime = RegimeContext(primary_regime_id="lehman", similarity_score=min(score, 0.99))
    elif score >= 0.55:
        state = "REDUCE_EXPOSURE"
        level = "high"
        confidence = "high"
        posture = "reduce_exposure"
        regime = RegimeContext(primary_regime_id="imf", similarity_score=min(score, 0.99))
    elif score >= 0.40:
        state = "WATCH"
        level = "elevated"
        confidence = "medium"
        posture = "watch_tighten"
        regime = RegimeContext(primary_regime_id="post_covid_normalization", similarity_score=max(score, 0.2))
    else:
        state = "GO"
        level = "normal"
        confidence = "low"
        posture = "maintain"
        regime = RegimeContext(primary_regime_id="post_covid_normalization", similarity_score=max(score, 0.1))

    insight = Insight7(
        market_liquidity_stress=min(max(score + 0.08, 0.0), 1.0),
        cross_asset_dislocation=min(max(score - 0.06, 0.0), 1.0),
        crowd_positioning_fragility=min(max(score + 0.02, 0.0), 1.0),
        volatility_regime_shift=min(max(score + 0.05, 0.0), 1.0),
        funding_pressure_signal=min(max(score - 0.03, 0.0), 1.0),
        macro_policy_shock_risk=min(max(score - 0.08, 0.0), 1.0),
        tail_event_pressure=min(max(score + 0.04, 0.0), 1.0),
    )

    response = MacroRiskWarningResponse(
        request_id=f"mrw_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        asset_scope=req.asset_scope,
        decision_state=state,
        risk_warning_level=level,
        confidence_band=confidence,
        insight_7=insight,
        regime_context=regime,
        recommended_operator_posture=posture,
    )
    if req.include_evidence_ref:
        response.evidence_ref = EvidenceRef(
            artifact_path="docs/final/artifacts/integrated_governance_v1_latest.json",
            artifact_hash_sha256=_artifact_hash(EVIDENCE_ARTIFACT),
        )
    return response


@app.post("/v1/risk/warning", response_model=MacroRiskWarningResponse)
async def get_macro_risk_warning(req: MacroRiskWarningRequest) -> MacroRiskWarningResponse:
    return build_macro_risk_warning_response(req)

