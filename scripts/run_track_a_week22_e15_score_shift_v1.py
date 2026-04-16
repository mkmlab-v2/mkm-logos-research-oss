# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-22 E1.5 with shifted router score coupling.
# Keywords: track_a, week22, e15, score_shift, routing
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
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e15_score_shift_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}
RISK_DOMAINS = {"ssot", "timing"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (report.get("compression_metrics", {}) or {}).get("cases", [])
    return {str((r or {}).get("id")): r for r in rows if str((r or {}).get("id"))}


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summarize(cases: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "global_token_saving_rate": _avg([float(c.get("token_saving_rate", 0.0)) for c in cases]),
        "avg_reconstruction_fidelity_jaccard": _avg([float(c.get("reconstruction_fidelity_jaccard", 0.0)) for c in cases]),
        "avg_sensitive_integrity": _avg([float(c.get("sensitive_integrity", 0.0)) for c in cases]),
        "sensitive_leak_rate": _avg([1.0 if bool(c.get("sensitive_leak", False)) else 0.0 for c in cases]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.49)
    ap.add_argument("--jaccard-floor", type=float, default=0.85)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    ap.add_argument("--risk-jaccard-tolerance", type=float, default=0.001)
    ap.add_argument("--general-jaccard-tolerance", type=float, default=0.004)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    gc = float(active_profile.get("general_max_saving_rate", 0.54))
    sc = float(active_profile.get("sensitive_max_saving_rate", 0.5))
    hc = float(active_profile.get("hangul_max_saving_rate", 0.48))

    router_on = evaluate_report(
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
    router_off = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=False,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    on_map = _build_case_map(router_on)
    off_map = _build_case_map(router_off)
    baseline = _summarize(list(on_map.values()))

    selected: list[dict[str, Any]] = []
    switched_to_off = 0
    blocked_by_tolerance = 0
    blocked_by_saving = 0
    switched_by_domain: dict[str, int] = {}
    for cid, on_case in on_map.items():
        off_case = off_map.get(cid)
        if not off_case:
            selected.append(on_case)
            continue

        domain = str((((on_case.get("route") or {}).get("domain")) or "unknown")).lower()
        on_j = float(on_case.get("reconstruction_fidelity_jaccard", 0.0))
        off_j = float(off_case.get("reconstruction_fidelity_jaccard", 0.0))
        on_s = float(on_case.get("token_saving_rate", 0.0))
        off_s = float(off_case.get("token_saving_rate", 0.0))

        tolerance = args.risk_jaccard_tolerance if domain in RISK_DOMAINS else args.general_jaccard_tolerance
        jaccard_ok = off_j >= (on_j - tolerance)
        saving_ok = off_s >= on_s

        if jaccard_ok and saving_ok:
            selected.append(off_case)
            switched_to_off += 1
            switched_by_domain[domain] = switched_by_domain.get(domain, 0) + 1
        else:
            selected.append(on_case)
            if not jaccard_ok:
                blocked_by_tolerance += 1
            if not saving_ok:
                blocked_by_saving += 1

    mixed = _summarize(selected)
    gate = {
        "saving_floor_ok": mixed["global_token_saving_rate"] >= args.saving_floor,
        "jaccard_floor_ok": mixed["avg_reconstruction_fidelity_jaccard"] >= args.jaccard_floor,
        "integrity_floor_ok": mixed["avg_sensitive_integrity"] >= args.integrity_floor,
    }
    decision = "GO_W22_E15_SCORE_SHIFT" if all(gate.values()) else "HOLD_W22_E15_NO_VIABLE"

    out_doc = {
        "schema": "track_a_week22_e15_score_shift_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "caps": {"general": gc, "sensitive": sc, "hangul": hc},
            "risk_domains": sorted(RISK_DOMAINS),
            "risk_jaccard_tolerance": args.risk_jaccard_tolerance,
            "general_jaccard_tolerance": args.general_jaccard_tolerance,
            "floors": {
                "saving_floor": args.saving_floor,
                "jaccard_floor": args.jaccard_floor,
                "integrity_floor": args.integrity_floor,
            },
        },
        "baseline_router_on": baseline,
        "candidate": {
            "switched_to_router_off_cases": switched_to_off,
            "blocked_by_tolerance_cases": blocked_by_tolerance,
            "blocked_by_saving_cases": blocked_by_saving,
            "switched_by_domain": switched_by_domain,
            "metrics": mixed,
            "delta_vs_baseline": {
                "saving": mixed["global_token_saving_rate"] - baseline["global_token_saving_rate"],
                "jaccard": mixed["avg_reconstruction_fidelity_jaccard"] - baseline["avg_reconstruction_fidelity_jaccard"],
                "integrity": mixed["avg_sensitive_integrity"] - baseline["avg_sensitive_integrity"],
            },
            "gate": gate,
        },
        "decision": decision,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "gate": gate}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
