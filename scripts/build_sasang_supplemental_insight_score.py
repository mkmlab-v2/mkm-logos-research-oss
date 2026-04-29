#!/usr/bin/env python3
"""Build supplemental insight score for Sasang commercialization packet.

Non-gating by policy: this score is supporting evidence only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_DNA = REPORTS / "bio_dna_constitution_final_approval_latest.json"
DEFAULT_SENTIMENT = ART / "fused_paper_cycle_weekly_latest.json"
DEFAULT_GEMATRIA_4D = ART / "gematria_4d_coupling_latest.json"
DEFAULT_OUT = ART / "sasang_supplemental_insight_score_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _clip(v: float) -> float:
    return max(0.0, min(1.0, v))


def _band(v: float) -> str:
    if v >= 0.8:
        return "HIGH"
    if v >= 0.6:
        return "MEDIUM"
    return "LOW"


def _dna_score(doc: dict[str, Any] | None) -> tuple[float, str]:
    if not isinstance(doc, dict):
        return 0.0, "missing_artifact"
    status = str(doc.get("approval_status") or "").upper()
    scope = doc.get("scope") or {}
    promotion_level = str(scope.get("promotion_level") or "")
    constrained = str(scope.get("operational_constraint") or "").lower()
    if status == "APPROVED" and "human_review_required" in constrained:
        if "CANDIDATE_READY_CONFIRMED" in promotion_level:
            return 1.0, "approved_candidate_ready_with_human_review_constraint"
        return 0.85, "approved_with_human_review_constraint"
    return 0.45, f"status={status or 'UNKNOWN'}"


def _sentiment_score(doc: dict[str, Any] | None) -> tuple[float, str]:
    if not isinstance(doc, dict):
        return 0.0, "missing_artifact"
    signals = ((doc.get("week_contract") or {}).get("signals") or {})
    sent = (signals.get("sentiment") or {}) if isinstance(signals, dict) else {}
    qual = str(sent.get("quality_flag") or "").lower()
    val = str(sent.get("value") or "").lower()
    decision = str(doc.get("decision") or "").upper()
    risk = doc.get("risk_signals") or {}
    hrel = str(risk.get("high_reliability_decision") or "").upper()

    score = 0.5
    if qual == "ok":
        score += 0.2
    if val in {"safe", "healthy", "stable"}:
        score += 0.2
    elif val in {"caution", "warning"}:
        score -= 0.1
    if hrel == "PASS":
        score += 0.1
    if decision == "HOLD":
        score -= 0.05
    return _clip(score), f"sentiment={val or 'unknown'}, decision={decision or 'UNKNOWN'}, quality={qual or 'unknown'}"


def _gematria_score(doc: dict[str, Any] | None) -> tuple[float, str]:
    if not isinstance(doc, dict):
        return 0.0, "missing_artifact"
    summary = doc.get("summary") or {}
    mean_coupling = float(summary.get("mean_coupling_strength") or 0.0)
    policy = str(summary.get("execution_policy") or "").lower()
    research_only = bool(doc.get("research_only"))
    point_count = int(summary.get("point_count") or 0)

    score = 0.0
    if point_count > 0:
        score += min(0.5, mean_coupling)
    if research_only and "non_trigger" in policy:
        score += 0.4
    else:
        score += 0.2
    return _clip(score), f"point_count={point_count}, mean_coupling={mean_coupling:.3f}, policy={policy or 'unknown'}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dna", type=Path, default=DEFAULT_DNA)
    ap.add_argument("--market-sentiment", type=Path, default=DEFAULT_SENTIMENT)
    ap.add_argument("--gematria-4d", type=Path, default=DEFAULT_GEMATRIA_4D)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    dna_doc = _read(args.dna)
    sentiment_doc = _read(args.market_sentiment)
    gem_doc = _read(args.gematria_4d)

    dna_score, dna_note = _dna_score(dna_doc)
    sentiment_score, sentiment_note = _sentiment_score(sentiment_doc)
    gem_score, gem_note = _gematria_score(gem_doc)

    weights = {"dna": 0.45, "market_sentiment": 0.30, "gematria_4d": 0.25}
    total = (
        (dna_score * weights["dna"])
        + (sentiment_score * weights["market_sentiment"])
        + (gem_score * weights["gematria_4d"])
    )
    total = _clip(total)

    payload = {
        "schema": "sasang_supplemental_insight_score_v1",
        "generated_at_utc": _now(),
        "non_gating_policy": True,
        "components": {
            "dna": {"score": round(dna_score, 6), "weight": weights["dna"], "note": dna_note},
            "market_sentiment": {
                "score": round(sentiment_score, 6),
                "weight": weights["market_sentiment"],
                "note": sentiment_note,
            },
            "gematria_4d": {"score": round(gem_score, 6), "weight": weights["gematria_4d"], "note": gem_note},
        },
        "supplemental_score": {
            "value": round(total, 6),
            "band": _band(total),
            "impact_on_go_no_go": "none_non_gating",
        },
        "evidence": {
            "dna": str(args.dna.resolve()) if dna_doc is not None else None,
            "market_sentiment": str(args.market_sentiment.resolve()) if sentiment_doc is not None else None,
            "gematria_4d": str(args.gematria_4d.resolve()) if gem_doc is not None else None,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"supplemental_score={payload['supplemental_score']['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
