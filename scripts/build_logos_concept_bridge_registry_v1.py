#!/usr/bin/env python3
"""Registry of logos concept_bridge artifacts + human_reviewed ratio ([HYPO])."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "logos_concept_bridge_registry_v1_latest.json"

DEFAULT_BRIDGE_PATHS = (
    ART / "logos_concept_bridge_semiconductor_poc_v1_latest.json",
    ART / "logos_concept_bridge_covenant_crisis_poc_v1_latest.json",
    ART / "logos_concept_bridge_cloud_resilience_poc_v1_latest.json",
    ART / "logos_concept_bridge_digital_trust_gemini_v1_latest.json",
    ART / "logos_concept_bridge_regime_watchfulness_gemini_v1_latest.json",
    ART / "logos_concept_bridge_mercy_compassion_gemini_v1_latest.json",
    ART / "logos_concept_bridge_wisdom_uncertainty_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q02_judgment_warning_collapse_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q05_hope_prolonged_stress_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q06_discipline_in_volatility_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q07_restoration_after_disruption_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q09_prudence_liquidity_stress_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q10_resilience_capitulation_phase_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q11_stability_after_volatility_shock_gemini_v1_latest.json",
    ART / "logos_concept_bridge_gold_q12_risk_excess_cycle_unwind_gemini_v1_latest.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_bridge(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def build_registry(bridge_paths: list[Path]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    human_reviewed_n = 0
    for path in bridge_paths:
        doc = _read_bridge(path)
        present = doc is not None
        policy = (doc or {}).get("policy") if isinstance((doc or {}).get("policy"), dict) else {}
        human = bool(policy.get("human_signoff_completed") or policy.get("human_reviewed"))
        if present and human:
            human_reviewed_n += 1
        query = (doc or {}).get("query") if isinstance((doc or {}).get("query"), dict) else {}
        entries.append(
            {
                "artifact_path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                "present": present,
                "concept_id": query.get("concept_id"),
                "label_ko": query.get("label_ko"),
                "path_count": len((doc or {}).get("paths") or []) if present else 0,
                "generation_method": policy.get("generation_method", "static_template"),
                "human_reviewed": human,
            }
        )
    n = len([e for e in entries if e["present"]])
    ratio = (human_reviewed_n / n) if n else 0.0
    governance_warning = human_reviewed_n == 0 and n >= 1
    return {
        "schema": "logos_concept_bridge_registry_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "bridge_count": n,
        "human_reviewed_count": human_reviewed_n,
        "human_reviewed_ratio": round(ratio, 4),
        "governance_warning_zero_human": governance_warning,
        "entries": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bridge-json", action="append", dest="bridge_jsons", default=[])
    args = ap.parse_args()

    paths = [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.bridge_jsons]
    if not paths:
        paths = list(DEFAULT_BRIDGE_PATHS)

    doc = build_registry(paths)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "bridge_count": doc["bridge_count"],
                "human_reviewed_ratio": doc["human_reviewed_ratio"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
