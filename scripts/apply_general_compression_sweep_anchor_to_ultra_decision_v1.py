#!/usr/bin/env python3
"""Wire general-rail sweep `best_go_candidate` into MULTILENS ultra decision + refresh V2 metrics.

Reads `docs/final/artifacts/general_compression_sweep_result_v1.json` (expects
`best_go_candidate` from `run_general_compression_sweep.py`), updates
`docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` selected_candidate,
re-runs the same evaluate_report path as `run_ultra_compression_default.py` (universal),
and writes refreshed `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
from scripts.report_multilens_performance_eval import evaluate_report

SWEEP_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "general_compression_sweep_result_v1.json"
DECISION_PATH = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _write(p: Path, doc: dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--decision", type=Path, default=DECISION_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sweep = _load(args.sweep)
    best = sweep.get("best_go_candidate")
    if not isinstance(best, dict) or not best.get("go"):
        print("FAIL: sweep has no best_go_candidate with go=true", file=sys.stderr)
        return 2

    decision = _load(args.decision)
    selected = {
        "strategy": str(best["strategy"]),
        "intensity": str(best["intensity"]),
        "use_hangul_principle": False,
        "general_max_saving_rate": float(best["general_max_saving_rate"]),
        "sensitive_max_saving_rate": float(best["sensitive_max_saving_rate"]),
        "hangul_max_saving_rate": float(best["hangul_max_saving_rate"]),
    }

    src_doc = _load(INPUT_V2)
    baseline_doc = _load(BASELINE_V2)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    apply_bridge_policy = env_apply_gematria_4d_bridge_policy()

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=selected["strategy"],
        intensity=selected["intensity"],
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=selected["general_max_saving_rate"],
        sensitive_max_saving_rate=selected["sensitive_max_saving_rate"],
        hangul_max_saving_rate=selected["hangul_max_saving_rate"],
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=apply_bridge_policy,
        include_cee_core=True,
    )
    cmp = report.get("compression_metrics") or {}
    qg = report.get("quality_gate") or {}
    selected["global_token_saving_rate"] = float(cmp.get("global_token_saving_rate", 0.0))
    selected["avg_reconstruction_fidelity_jaccard"] = float(cmp.get("avg_reconstruction_fidelity_jaccard", 0.0))
    selected["avg_sensitive_integrity"] = float(cmp.get("avg_sensitive_integrity", 0.0))
    selected["jaccard_drop_pp"] = float(qg.get("jaccard_drop_pp", 0.0))
    selected["canary_gate_ok"] = bool(qg.get("jaccard_guardrail_ok", False))

    decision["selected_candidate"] = selected
    decision["operational_anchor"] = {
        "schema": "general_rail_to_ultra_decision_anchor_v1",
        "sweep_artifact": str(args.sweep.resolve()).replace("\\", "/"),
        "sweep_profile": sweep.get("profile"),
        "best_go_candidate_snapshot": {
            "strategy": best.get("strategy"),
            "intensity": best.get("intensity"),
            "general_max_saving_rate": best.get("general_max_saving_rate"),
            "sensitive_max_saving_rate": best.get("sensitive_max_saving_rate"),
            "hangul_max_saving_rate": best.get("hangul_max_saving_rate"),
            "global_token_saving_rate": best.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": best.get("avg_reconstruction_fidelity_jaccard"),
        },
        "v2_bench_refresh_note": "selected_candidate performance fields re-measured on MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
    }
    decision["ts_utc"] = datetime.now(timezone.utc).isoformat()
    prev_note = str(decision.get("notes") or "").strip()
    anchor_line = (
        "Operational anchor: general-rail sweep best_go_candidate → ultra decision "
        f"({selected['strategy']}/{selected['intensity']} caps {selected['general_max_saving_rate']}/"
        f"{selected['sensitive_max_saving_rate']}/{selected['hangul_max_saving_rate']})."
    )
    decision["notes"] = (prev_note + "\n\n" if prev_note else "") + anchor_line

    report["active_profile"] = {
        "sla_track": "universal",
        "from_decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
        "strategy": selected["strategy"],
        "intensity": selected["intensity"],
        "general_max_saving_rate": selected["general_max_saving_rate"],
        "sensitive_max_saving_rate": selected["sensitive_max_saving_rate"],
        "hangul_max_saving_rate": selected["hangul_max_saving_rate"],
        "apply_gematria_4d_bridge_policy": apply_bridge_policy,
        "apply_gematria_4d_bridge_policy_env": env_apply_gematria_4d_bridge_policy(),
        "anchor_script": "scripts/apply_general_compression_sweep_anchor_to_ultra_decision_v1.py",
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "selected_candidate": selected}, ensure_ascii=False, indent=2))
        return 0

    _write(args.decision, decision)
    _write(ACTIVE_REPORT, report)
    print(json.dumps({"ok": True, "decision": str(args.decision), "active_report": str(ACTIVE_REPORT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
