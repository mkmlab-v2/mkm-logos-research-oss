#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _logos_decision(logos_md_text: str) -> str:
    t = logos_md_text.lower()
    if "consensus_sign=bull" in t or "direction hint=bull" in t:
        return "WATCH"
    if "consensus_sign=bear" in t:
        return "REDUCE"
    return "WATCH"


def main() -> int:
    ap = argparse.ArgumentParser(description="Single global coordinator for sasang/myeongni/logos fusion.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--sasang-json", type=Path, default=root / "reports" / "sasang_dna_market_reasoning_v1_latest.json")
    ap.add_argument("--myeongni-json", type=Path, default=root / "reports" / "myeongni_service_response_trackb_latest.json")
    ap.add_argument("--logos-md", type=Path, default=root / "reports" / "logos_track_b_commander_deep_report_latest.md")
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "mkm_global_coordinator_v1_latest.json",
    )
    ns = ap.parse_args()

    sas = _read_json(ns.sasang_json)
    mye = _read_json(ns.myeongni_json)
    logos_text = ns.logos_md.read_text(encoding="utf-8") if ns.logos_md.is_file() else ""

    sas_top = str((sas.get("summary", {}) or {}).get("latest_top_axis", ""))
    byung_state = str((sas.get("byungjeungyakri_transition", {}) or {}).get("state", "unknown"))
    sas_decision = "WATCH"
    if byung_state in ("stress", "crisis"):
        sas_decision = "REDUCE"
    elif sas_top == "TY":
        sas_decision = "WATCH"

    mye_decision = str((mye.get("final_action", {}) or {}).get("decision", "WATCH")).upper()
    logos_decision = _logos_decision(logos_text)

    lens_decisions = {
        "sasang": sas_decision,
        "myeongni": mye_decision,
        "logos": logos_decision,  # non-gating contextual input
    }
    primary = [lens_decisions["sasang"], lens_decisions["myeongni"]]
    agreement = sum(1 for x in primary if x == primary[0]) / len(primary) if primary else 0.0
    conflict_map = []
    if lens_decisions["sasang"] != lens_decisions["myeongni"]:
        conflict_map.append("sasang_vs_myeongni")
    if lens_decisions["logos"] != lens_decisions["sasang"]:
        conflict_map.append("logos_vs_sasang_context")

    # Global coordinator policy: SASANG+MYEONGNI primary, LOGOS contextual NON_GATING.
    if "REDUCE" in primary:
        final_action = "REDUCE"
    elif "GO" in primary:
        final_action = "GO"
    elif "WATCH" in primary:
        final_action = "WATCH"
    else:
        final_action = "HOLD"

    payload = {
        "schema": "mkm_global_coordinator_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "contracts": {
            "lens_output_contract": str((root / "docs" / "final" / "artifacts" / "schemas" / "mkm_lens_output_contract_v1.schema.json").resolve()),
            "global_fusion_contract": str((root / "docs" / "final" / "artifacts" / "schemas" / "mkm_global_fusion_contract_v1.schema.json").resolve()),
            "final_decision_contract": str((root / "docs" / "final" / "artifacts" / "schemas" / "mkm_final_decision_contract_v1.schema.json").resolve()),
        },
        "inputs": {
            "sasang": str(ns.sasang_json.resolve()),
            "myeongni": str(ns.myeongni_json.resolve()),
            "logos": str(ns.logos_md.resolve()),
        },
        "fusion": {
            "lens_decisions": lens_decisions,
            "agreement_rate": agreement,
            "consensus_decision": final_action,
            "conflict_map": conflict_map,
            "policy": "sasang+myeongni primary; logos non-gating contextual"
        },
        "decision": {
            "action": final_action,
            "risk_level": "elevated" if final_action == "REDUCE" else "moderate",
            "rationale": [
                f"sasang={sas_decision}",
                f"myeongni={mye_decision}",
                f"logos_context={logos_decision}",
            ],
        },
        "coordinator": {
            "mode": "single_global_coordinator",
            "conflict_resolution_policy": "primary lanes win; logos remains non-gating"
        },
        "notes": [
            "Single coordinator avoids duplicated coordinator-role conflicts.",
            "This is B-track fusion output only."
        ],
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} action={final_action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
