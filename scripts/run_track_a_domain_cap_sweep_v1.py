# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.5, M:0.2}
# Balance: 92
# Purpose: Sweep Track A caps to improve ssot/timing quality under saving floor.
# Keywords: track_a, domain_cap, sweep, commercialization, gate
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
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_domain_cap_sweep_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}
TARGET_DOMAINS = {"ssot", "timing"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _domain_avg_jaccard(report: dict[str, Any], domains: set[str]) -> float:
    rows = (report.get("compression_metrics", {}) or {}).get("cases", [])
    picked = [r for r in rows if str(((r.get("route") or {}).get("domain")) or "") in domains]
    if not picked:
        return 0.0
    return sum(float(r.get("reconstruction_fidelity_jaccard", 0.0)) for r in picked) / len(picked)


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
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.49)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    ap.add_argument("--gc-list", type=str, default="0.50,0.52,0.54,0.56")
    ap.add_argument("--sc-list", type=str, default="0.46,0.48,0.50")
    ap.add_argument("--hc-list", type=str, default="0.44,0.46,0.48")
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))

    baseline = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=float(active_profile.get("general_max_saving_rate", 0.54)),
        sensitive_max_saving_rate=float(active_profile.get("sensitive_max_saving_rate", 0.50)),
        hangul_max_saving_rate=float(active_profile.get("hangul_max_saving_rate", 0.48)),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )
    b_save, b_jac, b_int = _metrics(baseline)
    b_target_jac = _domain_avg_jaccard(baseline, TARGET_DOMAINS)

    gc_list = [float(x.strip()) for x in args.gc_list.split(",") if x.strip()]
    sc_list = [float(x.strip()) for x in args.sc_list.split(",") if x.strip()]
    hc_list = [float(x.strip()) for x in args.hc_list.split(",") if x.strip()]

    runs: list[dict[str, Any]] = []
    for gc in gc_list:
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
                    use_domain_router=True,
                    use_master_codebook_lexicon_v1=True,
                    include_gematria_metadata=True,
                    include_gematria_4d_bridge=True,
                    include_cee_core=True,
                )
                s, j, integ = _metrics(rep)
                target_j = _domain_avg_jaccard(rep, TARGET_DOMAINS)
                row = {
                    "caps": {"general": gc, "sensitive": sc, "hangul": hc},
                    "saving": s,
                    "jaccard": j,
                    "integrity": integ,
                    "target_domain_jaccard": target_j,
                    "delta_saving_vs_baseline": s - b_save,
                    "delta_jaccard_vs_baseline": j - b_jac,
                    "delta_target_domain_jaccard_vs_baseline": target_j - b_target_jac,
                    "saving_floor_ok": s >= args.saving_floor,
                    "integrity_floor_ok": integ >= args.integrity_floor,
                }
                runs.append(row)

    viable = [r for r in runs if r["saving_floor_ok"] and r["integrity_floor_ok"]]
    best = sorted(
        viable,
        key=lambda r: (
            r["delta_target_domain_jaccard_vs_baseline"],
            r["delta_jaccard_vs_baseline"],
            r["saving"],
        ),
        reverse=True,
    )[0] if viable else None

    out_doc = {
        "schema": "track_a_domain_cap_sweep_v1",
        "generated_at_utc": _now_utc(),
        "baseline": {
            "saving": b_save,
            "jaccard": b_jac,
            "integrity": b_int,
            "target_domain_jaccard": b_target_jac,
            "caps": {
                "general": float(active_profile.get("general_max_saving_rate", 0.54)),
                "sensitive": float(active_profile.get("sensitive_max_saving_rate", 0.50)),
                "hangul": float(active_profile.get("hangul_max_saving_rate", 0.48)),
            },
        },
        "sweep_space": {"gc_list": gc_list, "sc_list": sc_list, "hc_list": hc_list},
        "run_count": len(runs),
        "viable_count": len(viable),
        "recommended": best,
        "decision": "GO_RECOMMENDED_CAPS" if best else "HOLD_BASELINE_TRACK_A",
        "runs": sorted(runs, key=lambda r: r["delta_target_domain_jaccard_vs_baseline"], reverse=True),
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": out_doc["decision"], "recommended": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
