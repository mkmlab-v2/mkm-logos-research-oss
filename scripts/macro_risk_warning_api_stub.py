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
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PACK = ROOT / "docs" / "final" / "artifacts" / "track_c_evidence_pack_latest.json"
EVIDENCE_ARTIFACT = ROOT / "docs" / "final" / "artifacts" / "integrated_governance_v1_latest.json"
FRAGILITY_ARTIFACT = ROOT / "docs" / "final" / "artifacts" / "fragility_composite_v1_latest.json"
NARRATIVE_TEMPLATE_ARTIFACT = ROOT / "docs" / "final" / "artifacts" / "macro_risk_non_gating_template_v1.json"

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


class FragilityComposite(BaseModel):
    schema_version: str = "fragility_composite_v1"
    gate: str
    score_0_100: float = Field(ge=0.0, le=100.0)
    z_move: float
    z_vix: float
    z_hy_oas: float
    z_dxy_vol: float
    hard_trigger: bool = False
    fragility_cluster: bool = False
    stress_persistence: bool = False


class NonGatingNarrative(BaseModel):
    template_version: str = "macro_risk_non_gating_template_v1"
    policy_tag: str = "[NON_GATING]"
    stage: str
    field: str
    logos: str
    conflict: str
    action: str
    trigger_basis: list[str] = Field(default_factory=list)
    state_4d: dict[str, float] = Field(default_factory=dict)
    quaternion_signal: str = "not_available"


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
    fragility_composite: FragilityComposite | None = None
    non_gating_narrative: NonGatingNarrative | None = None
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


def _load_fragility_snapshot() -> dict[str, Any]:
    if not FRAGILITY_ARTIFACT.is_file():
        return {}
    try:
        doc = json.loads(FRAGILITY_ARTIFACT.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}
    return doc


def _load_narrative_templates() -> dict[str, Any]:
    if not NARRATIVE_TEMPLATE_ARTIFACT.is_file():
        return {}
    try:
        doc = json.loads(NARRATIVE_TEMPLATE_ARTIFACT.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}
    return doc


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_4d_state(z_scores: dict[str, float]) -> dict[str, float]:
    # 4D labels: stress/liquidity/credit/currency in [0,1].
    return {
        "stress": round(_to_float(abs(z_scores.get("move", 0.0))) / 3.0, 6),
        "liquidity": round(_to_float(abs(z_scores.get("vix", 0.0))) / 3.0, 6),
        "credit": round(_to_float(abs(z_scores.get("hy_oas", 0.0))) / 3.0, 6),
        "currency": round(_to_float(abs(z_scores.get("dxy_vol", 0.0))) / 3.0, 6),
    }


def _build_quaternion_signal(fragility_doc: dict[str, Any], gate: str) -> str:
    delta = fragility_doc.get("quaternion_delta")
    if isinstance(delta, dict):
        magnitude = _to_float(delta.get("magnitude"), -1.0)
        if magnitude >= 0.0:
            if magnitude >= 0.55:
                return "phase_shift_high"
            if magnitude >= 0.30:
                return "phase_shift_mid"
            return "phase_shift_low"
    return "phase_shift_assumed_high" if gate == "RED" else "phase_shift_assumed_mid" if gate == "AMBER" else "phase_shift_assumed_low"


def _build_narrative(gate: str, hard_trigger: bool, fragility_cluster: bool, z_scores: dict[str, float], fragility_doc: dict[str, Any]) -> NonGatingNarrative:
    templates = _load_narrative_templates()
    by_gate = templates.get("templates_by_gate") if isinstance(templates.get("templates_by_gate"), dict) else {}
    tpl = by_gate.get(gate) if isinstance(by_gate.get(gate), dict) else {}

    default_map: dict[str, dict[str, str]] = {
        "RED": {
            "stage": "late_babel_to_exodus_transition",
            "field": "구조적 파열 고위험 구간",
            "logos": "출애굽 초기 징후 강화로 해석 가능한 전이 압력",
            "conflict": "레버리지 방어 vs 생존성 우선",
            "action": "REDUCE / PREPARE",
        },
        "AMBER": {
            "stage": "wilderness_preheat",
            "field": "구조적 균열 관측 구간",
            "logos": "광야 진입 전 변동성 확대 단계",
            "conflict": "추세 추종 vs 리스크 예열 관리",
            "action": "WATCH / TIGHTEN",
        },
        "GREEN": {
            "stage": "stable_watch",
            "field": "정상 구간 또는 약한 스트레스",
            "logos": "안정 국면의 보수적 관측",
            "conflict": "수익 추구 vs 예방적 경계",
            "action": "MAINTAIN / OBSERVE",
        },
    }
    base = default_map.get(gate, default_map["GREEN"])
    action = str(tpl.get("action") or base["action"])
    if gate == "GREEN" and (hard_trigger or fragility_cluster):
        action = "WATCH / PREPARE"

    trigger_basis: list[str] = [f"gate:{gate}"]
    if hard_trigger:
        trigger_basis.append("hard_trigger:true")
    if fragility_cluster:
        trigger_basis.append("fragility_cluster:true")

    return NonGatingNarrative(
        template_version=str(templates.get("schema") or "macro_risk_non_gating_template_v1"),
        stage=str(tpl.get("stage") or base["stage"]),
        field=str(tpl.get("field") or base["field"]),
        logos=str(tpl.get("logos") or base["logos"]),
        conflict=str(tpl.get("conflict") or base["conflict"]),
        action=action,
        trigger_basis=trigger_basis,
        state_4d=_build_4d_state(z_scores),
        quaternion_signal=_build_quaternion_signal(fragility_doc, gate),
    )


def build_macro_risk_warning_response(req: MacroRiskWarningRequest) -> MacroRiskWarningResponse:
    score = _load_governance_score()
    fragility_doc = _load_fragility_snapshot()
    gate = str(fragility_doc.get("gate", "")).upper()
    fragility_score = _to_float((fragility_doc.get("score") or {}).get("scaled_0_100"), -1.0)
    gate_details = fragility_doc.get("gate_details") if isinstance(fragility_doc.get("gate_details"), dict) else {}
    hard_trigger = bool(gate_details.get("hard_trigger", False))
    stress_persistence = bool(gate_details.get("stress_persistence", False))
    fragility_cluster = bool(gate_details.get("fragility_cluster", False))

    if gate in {"GREEN", "AMBER", "RED"} and fragility_score >= 0.0:
        if gate == "RED" and (hard_trigger or stress_persistence):
            state = "FORCE_HOLD"
            level = "critical"
            confidence = "high"
            posture = "halt_new_entries"
            regime = RegimeContext(primary_regime_id="lehman", similarity_score=min(max(fragility_score / 100.0, 0.5), 0.99))
        elif gate == "RED":
            state = "REDUCE_EXPOSURE"
            level = "high"
            confidence = "high"
            posture = "reduce_exposure"
            regime = RegimeContext(primary_regime_id="imf", similarity_score=min(max(fragility_score / 100.0, 0.4), 0.99))
        elif gate == "AMBER":
            state = "WATCH"
            level = "elevated"
            confidence = "medium"
            posture = "watch_tighten"
            regime = RegimeContext(primary_regime_id="post_covid_normalization", similarity_score=min(max(fragility_score / 100.0, 0.3), 0.85))
        else:
            state = "GO"
            level = "normal"
            confidence = "low"
            posture = "maintain"
            regime = RegimeContext(primary_regime_id="post_covid_normalization", similarity_score=min(max(fragility_score / 100.0, 0.1), 0.7))
    elif score >= 0.75:
        state = "FORCE_HOLD"
        level = "critical"
        confidence = "high"
        posture = "halt_new_entries"
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

    if gate in {"GREEN", "AMBER", "RED"} and fragility_score >= 0.0:
        z_scores = fragility_doc.get("z_scores") if isinstance(fragility_doc.get("z_scores"), dict) else {}
        response.fragility_composite = FragilityComposite(
            gate=gate,
            score_0_100=_to_float(fragility_score),
            z_move=_to_float(z_scores.get("move", 0.0)),
            z_vix=_to_float(z_scores.get("vix", 0.0)),
            z_hy_oas=_to_float(z_scores.get("hy_oas", 0.0)),
            z_dxy_vol=_to_float(z_scores.get("dxy_vol", 0.0)),
            hard_trigger=hard_trigger,
            fragility_cluster=fragility_cluster,
            stress_persistence=stress_persistence,
        )
        response.non_gating_narrative = _build_narrative(
            gate=gate,
            hard_trigger=hard_trigger,
            fragility_cluster=fragility_cluster,
            z_scores={k: _to_float(v) for k, v in z_scores.items()},
            fragility_doc=fragility_doc,
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

