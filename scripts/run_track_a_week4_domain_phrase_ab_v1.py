# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-4 domain-specific phrase policy A/B experiment.
# Keywords: track_a, week4, domain_phrase, ab_test, ssot
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
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_experiment_pack_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_domain_phrase_ab_v1.json"

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


def _domain_avg_jaccard(report: dict[str, Any], target_domains: set[str]) -> float:
    rows = (report.get("compression_metrics", {}) or {}).get("cases", [])
    picked = [r for r in rows if str(((r.get("route") or {}).get("domain")) or "") in target_domains]
    if not picked:
        return 0.0
    return sum(float(r.get("reconstruction_fidelity_jaccard", 0.0)) for r in picked) / len(picked)


def _read_e1_config(pack_doc: dict[str, Any]) -> tuple[list[str], list[str]]:
    experiments = ((pack_doc.get("pack") or {}).get("experiments") or [])
    e1 = next((x for x in experiments if str(x.get("id")) == "W4-E1"), {})
    cfg = e1.get("config") or {}
    return list(cfg.get("target_domains") or ["ssot"]), list(cfg.get("phrase_seed_tokens") or [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--pack", type=Path, default=PACK)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--target-domains", type=str, default="")
    ap.add_argument("--phrase-tokens", type=str, default="")
    ap.add_argument("--gc-list", type=str, default="0.54,0.56,0.58")
    ap.add_argument("--saving-floor", type=float, default=0.475)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    ap.add_argument("--jaccard-drop-limit", type=float, default=0.01)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    pack_doc = _load_json(args.pack if args.pack.is_absolute() else ROOT / args.pack)

    default_domains, default_tokens = _read_e1_config(pack_doc)
    target_domains = [x.strip().lower() for x in args.target_domains.split(",") if x.strip()] or default_domains
    phrase_tokens = [x.strip().lower() for x in args.phrase_tokens.split(",") if x.strip()] or default_tokens
    target_domain_set = set(target_domains)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    sc = float(active_profile.get("sensitive_max_saving_rate", 0.5))
    hc = float(active_profile.get("hangul_max_saving_rate", 0.48))
    baseline_gc = float(active_profile.get("general_max_saving_rate", 0.54))

    baseline = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=baseline_gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )
    b_save, b_jac, b_int = _metric_triplet(baseline)
    b_domain_jac = _domain_avg_jaccard(baseline, target_domain_set)

    gc_list = [float(x.strip()) for x in args.gc_list.split(",") if x.strip()]
    treatments: list[dict[str, Any]] = []
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
        d_jac = _domain_avg_jaccard(rep, target_domain_set)
        treatments.append(
            {
                "caps": {"general": gc, "sensitive": sc, "hangul": hc},
                "target_domains": target_domains,
                "phrase_tokens": phrase_tokens,
                "saving": s,
                "jaccard": j,
                "integrity": integ,
                "target_domain_jaccard": d_jac,
                "delta_vs_baseline": {
                    "saving": s - b_save,
                    "jaccard": j - b_jac,
                    "integrity": integ - b_int,
                    "target_domain_jaccard": d_jac - b_domain_jac,
                },
                "gate": {
                    "saving_floor_ok": s >= args.saving_floor,
                    "integrity_floor_ok": integ >= args.integrity_floor,
                    "target_domain_jaccard_ok": d_jac >= (b_domain_jac - args.jaccard_drop_limit),
                },
            }
        )

    viable = [
        r
        for r in treatments
        if r["gate"]["saving_floor_ok"] and r["gate"]["integrity_floor_ok"] and r["gate"]["target_domain_jaccard_ok"]
    ]
    recommended = sorted(viable, key=lambda r: (r["target_domain_jaccard"], r["saving"]), reverse=True)[0] if viable else None

    out_doc = {
        "schema": "track_a_week4_domain_phrase_ab_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "pack": str(args.pack),
            "target_domains": target_domains,
            "phrase_tokens": phrase_tokens,
            "gc_list": gc_list,
            "floors": {
                "saving_floor": args.saving_floor,
                "integrity_floor": args.integrity_floor,
                "jaccard_drop_limit": args.jaccard_drop_limit,
            },
        },
        "baseline": {
            "saving": b_save,
            "jaccard": b_jac,
            "integrity": b_int,
            "target_domain_jaccard": b_domain_jac,
            "caps": {"general": baseline_gc, "sensitive": sc, "hangul": hc},
        },
        "treatments": treatments,
        "viable_count": len(viable),
        "recommended": recommended,
        "decision": "GO_W4_E2_TIMING_PHRASE" if recommended else "HOLD_W4_E1_NO_VIABLE",
        "next_action": (
            "Proceed to W4-E2 timing-domain phrase policy with same router-on guard."
            if recommended
            else "Keep baseline router-on and still run W4-E2 to test timing-specific recovery."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": out_doc["decision"], "viable_count": len(viable)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
