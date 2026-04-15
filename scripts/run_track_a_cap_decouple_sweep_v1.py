# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-3 D2 cap-decoupling sweep after routing A/B.
# Keywords: track_a, cap_decouple, sweep, saving_recovery, jaccard
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
ROUTING_AB = ROOT / "docs" / "final" / "artifacts" / "track_a_routing_condition_ab_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_cap_decouple_sweep_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(report: dict[str, Any]) -> tuple[float, float, float]:
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
    ap.add_argument("--routing-ab", type=Path, default=ROUTING_AB)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.48)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    ap.add_argument("--jaccard-floor", type=float, default=0.80)
    ap.add_argument("--gc-fixed", type=float, default=0.54)
    ap.add_argument("--sc-list", type=str, default="0.46,0.48,0.50")
    ap.add_argument("--hc-list", type=str, default="0.44,0.46,0.48")
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    routing_doc = _load_json(args.routing_ab if args.routing_ab.is_absolute() else ROOT / args.routing_ab)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))

    selected = str(((routing_doc.get("candidate") or {}).get("name")) or "arm_a_router_on")
    use_router = selected != "arm_b_router_off"

    sc_list = [float(x.strip()) for x in args.sc_list.split(",") if x.strip()]
    hc_list = [float(x.strip()) for x in args.hc_list.split(",") if x.strip()]
    gc = float(args.gc_fixed)

    runs: list[dict[str, Any]] = []
    for sc in sc_list:
        for hc in hc_list:
            rep = evaluate_report(
                input_doc,
                source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
                mode="experimental",
                strategy=strategy,
                intensity=intensity,
                must_keep=set(BASE_MUST_KEEP),
                general_max_saving_rate=gc,
                sensitive_max_saving_rate=sc,
                hangul_max_saving_rate=hc,
                use_domain_router=use_router,
                use_master_codebook_lexicon_v1=True,
                include_gematria_metadata=True,
                include_gematria_4d_bridge=True,
                include_cee_core=True,
            )
            save, jac, integ = _metrics(rep)
            runs.append(
                {
                    "caps": {"general": gc, "sensitive": sc, "hangul": hc},
                    "use_domain_router": use_router,
                    "saving": save,
                    "jaccard": jac,
                    "integrity": integ,
                    "saving_floor_ok": save >= args.saving_floor,
                    "jaccard_floor_ok": jac >= args.jaccard_floor,
                    "integrity_floor_ok": integ >= args.integrity_floor,
                }
            )

    viable = [
        r
        for r in runs
        if r["saving_floor_ok"] and r["jaccard_floor_ok"] and r["integrity_floor_ok"]
    ]
    recommended = (
        sorted(viable, key=lambda r: (r["saving"], r["jaccard"]), reverse=True)[0]
        if viable
        else None
    )
    best_jaccard = sorted(runs, key=lambda r: r["jaccard"], reverse=True)[0] if runs else None

    out_doc = {
        "schema": "track_a_cap_decouple_sweep_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "routing_ab": str(args.routing_ab),
            "routing_selected": selected,
            "sweep_space": {"gc_fixed": gc, "sc_list": sc_list, "hc_list": hc_list},
            "floors": {
                "saving_floor": args.saving_floor,
                "jaccard_floor": args.jaccard_floor,
                "integrity_floor": args.integrity_floor,
            },
        },
        "run_count": len(runs),
        "viable_count": len(viable),
        "recommended": recommended,
        "best_jaccard_observed": best_jaccard,
        "decision": "GO_W3_D3_PHRASE_PROFILE" if recommended else "HOLD_W3_D2_NO_VIABLE",
        "next_action": (
            "Use recommended caps for W3-D3 conservative phrase-first profile test."
            if recommended
            else "Fallback to router-on baseline and test conservative phrase-first profile directly."
        ),
        "runs": sorted(runs, key=lambda r: (r["jaccard"], r["saving"]), reverse=True),
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
