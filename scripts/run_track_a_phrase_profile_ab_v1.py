# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-3 D3 conservative phrase-first profile A/B.
# Keywords: track_a, phrase_first, ab_test, saving_recovery, jaccard
#!/usr/bin/env python3
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

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_A = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
PRIORITY_RULES = ROOT / "docs" / "final" / "artifacts" / "track_a_failure_pattern_rules_priority_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_phrase_profile_ab_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_triplet(report: dict[str, Any]) -> tuple[float, float, float]:
    m = report.get("compression_metrics", {})
    return (
        float(m.get("global_token_saving_rate", 0.0)),
        float(m.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        float(m.get("avg_sensitive_integrity", 0.0)),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--priority-rules", type=Path, default=PRIORITY_RULES)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--phrase-top-n", type=int, default=5)
    ap.add_argument("--gc-list", type=str, default="0.54,0.56,0.58")
    ap.add_argument("--saving-floor", type=float, default=0.485)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    ap.add_argument("--jaccard-tolerance", type=float, default=-0.02)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    rules_doc = _load_json(args.priority_rules if args.priority_rules.is_absolute() else ROOT / args.priority_rules)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    sc = float(active_profile.get("sensitive_max_saving_rate", 0.5))
    hc = float(active_profile.get("hangul_max_saving_rate", 0.48))

    phrase_tokens = [
        str(row.get("token") or "").strip().lower()
        for row in rules_doc.get("must_keep_candidates", [])
        if str(row.get("token") or "").strip()
    ][: max(1, args.phrase_top_n)]
    phrase_tokens = [t for t in phrase_tokens if len(t) >= 2]

    baseline = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=float(active_profile.get("general_max_saving_rate", 0.54)),
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )
    b_save, b_jac, b_int = _metric_triplet(baseline)

    gc_list = [float(x.strip()) for x in args.gc_list.split(",") if x.strip()]
    treatment_runs: list[dict[str, Any]] = []
    for gc in gc_list:
        rep = evaluate_report(
            input_doc,
            source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            mode="experimental",
            strategy=strategy,
            intensity=intensity,
            must_keep=set(BASE_MUST_KEEP) | set(phrase_tokens),
            general_max_saving_rate=gc,
            sensitive_max_saving_rate=sc,
            hangul_max_saving_rate=hc,
            use_domain_router=True,
            use_master_codebook_lexicon_v1=True,
            include_gematria_metadata=True,
            include_gematria_4d_bridge=True,
            include_cee_core=True,
        )
        s, j, integ = _metric_triplet(rep)
        treatment_runs.append(
            {
                "profile": "router_on_phrase_first_conservative",
                "caps": {"general": gc, "sensitive": sc, "hangul": hc},
                "must_keep_phrase_tokens": phrase_tokens,
                "saving": s,
                "jaccard": j,
                "integrity": integ,
                "delta_vs_baseline": {
                    "saving": s - b_save,
                    "jaccard": j - b_jac,
                    "integrity": integ - b_int,
                },
                "gate": {
                    "saving_floor_ok": s >= args.saving_floor,
                    "integrity_floor_ok": integ >= args.integrity_floor,
                    "jaccard_tolerance_ok": (j - b_jac) >= args.jaccard_tolerance,
                },
            }
        )

    viable = [
        r
        for r in treatment_runs
        if r["gate"]["saving_floor_ok"] and r["gate"]["integrity_floor_ok"] and r["gate"]["jaccard_tolerance_ok"]
    ]
    recommended = sorted(viable, key=lambda r: (r["jaccard"], r["saving"]), reverse=True)[0] if viable else None

    out_doc = {
        "schema": "track_a_phrase_profile_ab_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "priority_rules": str(args.priority_rules),
            "phrase_top_n": args.phrase_top_n,
            "gc_list": gc_list,
            "floors": {
                "saving_floor": args.saving_floor,
                "integrity_floor": args.integrity_floor,
                "jaccard_tolerance": args.jaccard_tolerance,
            },
        },
        "baseline_router_on": {
            "saving": b_save,
            "jaccard": b_jac,
            "integrity": b_int,
            "caps": {
                "general": float(active_profile.get("general_max_saving_rate", 0.54)),
                "sensitive": sc,
                "hangul": hc,
            },
            "must_keep_terms": sorted(BASE_MUST_KEEP),
        },
        "treatments": treatment_runs,
        "viable_count": len(viable),
        "recommended": recommended,
        "decision": "GO_W3_D4_POLICY_REPLAY" if recommended else "HOLD_W3_D3_NO_VIABLE",
        "next_action": (
            "Replay recommended phrase-first profile under policy floor gate for W3-D4."
            if recommended
            else "Keep baseline router-on profile; no phrase-first candidate met D3 gate."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out_path), "decision": out_doc["decision"], "viable_count": len(viable)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
