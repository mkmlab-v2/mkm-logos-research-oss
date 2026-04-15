# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-18 E3 coupled veto throttle with domain budget sweep.
# Keywords: track_a, week18, coupled_veto, domain_budget, sweep
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week18_hypothesis_pack_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week18_coupled_veto_domain_budget_sweep_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_e3_config(pack_doc: dict[str, Any]) -> tuple[list[float], list[float], list[float], list[int]]:
    experiments = ((pack_doc.get("pack") or {}).get("experiments") or [])
    e3 = next((x for x in experiments if str(x.get("id")) == "W18-E3"), {})
    cfg = e3.get("config") or {}
    confidence_gate_grid = [float(x) for x in (cfg.get("confidence_gate_grid") or [])]
    throttle_quota_grid = [float(x) for x in (cfg.get("throttle_quota_grid") or [])]
    rollback_penalty_grid = [float(x) for x in (cfg.get("rollback_penalty_grid") or [])]
    domain_quota_cap_grid = [int(x) for x in (cfg.get("domain_quota_cap_grid") or [])]
    return (
        confidence_gate_grid or [0.53, 0.57, 0.61],
        throttle_quota_grid or [0.12, 0.14, 0.16],
        rollback_penalty_grid or [0.025, 0.04, 0.055],
        domain_quota_cap_grid or [2, 3, 4],
    )


def _build_case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (report.get("compression_metrics", {}) or {}).get("cases", [])
    return {str((r or {}).get("id")): r for r in rows if str((r or {}).get("id"))}


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _hash_unit(value: str) -> float:
    raw = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return int(raw, 16) / 0xFFFFFFFF


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
    ap.add_argument("--pack", type=Path, default=PACK)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.49)
    ap.add_argument("--jaccard-floor", type=float, default=0.85)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    pack_doc = _load_json(args.pack if args.pack.is_absolute() else ROOT / args.pack)
    confidence_gates, throttle_quotas, rollback_penalties, domain_quota_caps = _read_e3_config(pack_doc)

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
    total_cases = len(on_map)

    runs: list[dict[str, Any]] = []
    for confidence_gate in confidence_gates:
        for throttle_quota in throttle_quotas:
            for rollback_penalty in rollback_penalties:
                for domain_quota_cap in domain_quota_caps:
                    selected: list[dict[str, Any]] = []
                    switched_to_off = 0
                    confidence_blocked = 0
                    quota_blocked = 0
                    domain_quota_blocked = 0
                    veto_blocked = 0
                    total = 0
                    quota_limit = max(0, int(total_cases * max(0.0, min(0.5, throttle_quota))))
                    switched_by_domain: dict[str, int] = {}

                    for cid, on_case in on_map.items():
                        off_case = off_map.get(cid)
                        if not off_case:
                            selected.append(on_case)
                            total += 1
                            continue
                        confidence = _hash_unit(f"w18-e3:conf:{cid}:{confidence_gate}:{domain_quota_cap}")
                        if confidence >= confidence_gate:
                            selected.append(on_case)
                            confidence_blocked += 1
                            total += 1
                            continue
                        if switched_to_off >= quota_limit:
                            selected.append(on_case)
                            quota_blocked += 1
                            total += 1
                            continue

                        domain = str((((on_case.get("route") or {}).get("domain")) or "unknown")).lower()
                        current_domain_switched = switched_by_domain.get(domain, 0)
                        if current_domain_switched >= max(0, domain_quota_cap):
                            selected.append(on_case)
                            domain_quota_blocked += 1
                            total += 1
                            continue

                        on_s = float(on_case.get("token_saving_rate", 0.0))
                        off_s = float(off_case.get("token_saving_rate", 0.0))
                        on_j = float(on_case.get("reconstruction_fidelity_jaccard", 0.0))
                        off_j = float(off_case.get("reconstruction_fidelity_jaccard", 0.0))
                        jaccard_drop = max(0.0, on_j - off_j)
                        saving_gap = max(0.0, args.saving_floor - off_s)
                        veto_score = (jaccard_drop * 0.65) + (saving_gap * 0.35)
                        use_off = veto_score <= rollback_penalty
                        if not use_off:
                            veto_blocked += 1
                        selected.append(off_case if use_off else on_case)
                        if use_off:
                            switched_to_off += 1
                            switched_by_domain[domain] = current_domain_switched + 1
                        total += 1

                    mixed = _summarize(selected)
                    row = {
                        "confidence_gate": confidence_gate,
                        "throttle_quota": throttle_quota,
                        "rollback_penalty": rollback_penalty,
                        "domain_quota_cap": domain_quota_cap,
                        "quota_limit_cases": quota_limit,
                        "switched_to_router_off_cases": switched_to_off,
                        "switched_by_domain": switched_by_domain,
                        "confidence_blocked_cases": confidence_blocked,
                        "quota_blocked_cases": quota_blocked,
                        "domain_quota_blocked_cases": domain_quota_blocked,
                        "veto_blocked_cases": veto_blocked,
                        "switched_ratio": (switched_to_off / total) if total else 0.0,
                        "metrics": mixed,
                        "delta_vs_baseline": {
                            "saving": mixed["global_token_saving_rate"] - baseline["global_token_saving_rate"],
                            "jaccard": mixed["avg_reconstruction_fidelity_jaccard"] - baseline["avg_reconstruction_fidelity_jaccard"],
                            "integrity": mixed["avg_sensitive_integrity"] - baseline["avg_sensitive_integrity"],
                        },
                        "gate": {
                            "saving_floor_ok": mixed["global_token_saving_rate"] >= args.saving_floor,
                            "jaccard_floor_ok": mixed["avg_reconstruction_fidelity_jaccard"] >= args.jaccard_floor,
                            "integrity_floor_ok": mixed["avg_sensitive_integrity"] >= args.integrity_floor,
                        },
                    }
                    runs.append(row)

    viable = [r for r in runs if all(r["gate"].values())]
    recommended = (
        sorted(
            viable,
            key=lambda r: (
                r["metrics"]["avg_reconstruction_fidelity_jaccard"],
                r["metrics"]["global_token_saving_rate"],
            ),
            reverse=True,
        )[0]
        if viable
        else None
    )
    decision = "GO_W18_E4_POLICY_REPLAY" if recommended else "HOLD_W18_E3_NO_VIABLE"

    out_doc = {
        "schema": "track_a_week18_coupled_veto_domain_budget_sweep_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "pack": str(args.pack),
            "confidence_gate_grid": confidence_gates,
            "throttle_quota_grid": throttle_quotas,
            "rollback_penalty_grid": rollback_penalties,
            "domain_quota_cap_grid": domain_quota_caps,
            "caps": {"general": gc, "sensitive": sc, "hangul": hc},
            "floors": {
                "saving_floor": args.saving_floor,
                "jaccard_floor": args.jaccard_floor,
                "integrity_floor": args.integrity_floor,
            },
        },
        "baseline_router_on": baseline,
        "run_count": len(runs),
        "viable_count": len(viable),
        "recommended": recommended,
        "decision": decision,
        "next_action": (
            "Proceed to W18-E4 policy replay."
            if decision == "GO_W18_E4_POLICY_REPLAY"
            else "Keep baseline and continue to W18-E4 replay with HOLD evidence."
        ),
        "runs": sorted(
            runs,
            key=lambda r: (
                r["metrics"]["avg_reconstruction_fidelity_jaccard"],
                r["metrics"]["global_token_saving_rate"],
            ),
            reverse=True,
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "viable_count": len(viable)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
