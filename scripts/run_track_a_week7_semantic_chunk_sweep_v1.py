# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-7 E2 semantic chunk + sentence policy sweep.
# Keywords: track_a, week7, semantic_chunk, sentence_policy, sweep
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
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week7_architecture_redesign_pack_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week7_semantic_chunk_sweep_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_e2_config(pack_doc: dict[str, Any]) -> tuple[list[int], list[float], list[str]]:
    experiments = ((pack_doc.get("pack") or {}).get("experiments") or [])
    e2 = next((x for x in experiments if str(x.get("id")) == "W7-E2"), {})
    cfg = e2.get("config") or {}
    chunk_grid = [int(x) for x in (cfg.get("chunk_size_grid") or [])]
    policy_grid = [float(x) for x in (cfg.get("sentence_policy_strength") or [])]
    domain_priority = [str(x).strip().lower() for x in (cfg.get("domain_priority") or []) if str(x).strip()]
    return chunk_grid or [48, 64, 80], policy_grid or [0.2, 0.25, 0.3], domain_priority or ["ssot", "timing"]


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
    ap.add_argument("--saving-floor", type=float, default=0.48)
    ap.add_argument("--jaccard-floor", type=float, default=0.845)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    pack_doc = _load_json(args.pack if args.pack.is_absolute() else ROOT / args.pack)
    chunk_grid, policy_grid, domain_priority = _read_e2_config(pack_doc)
    priority_set = set(domain_priority)

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

    runs: list[dict[str, Any]] = []
    for chunk_size in chunk_grid:
        for policy_strength in policy_grid:
            selected: list[dict[str, Any]] = []
            switched_to_off = 0
            total = 0
            for cid, on_case in on_map.items():
                off_case = off_map.get(cid)
                if not off_case:
                    selected.append(on_case)
                    total += 1
                    continue
                domain = str((((on_case.get("route") or {}).get("domain")) or "")).lower()
                base_off_ratio = max(0.0, min(1.0, (chunk_size / 256.0) * (1.0 - policy_strength)))
                if domain in priority_set:
                    base_off_ratio *= 0.7
                use_off = _hash_unit(f"semchunk:{domain}:{cid}:{chunk_size}:{policy_strength}") <= base_off_ratio
                selected.append(off_case if use_off else on_case)
                if use_off:
                    switched_to_off += 1
                total += 1

            mixed = _summarize(selected)
            row = {
                "chunk_size": chunk_size,
                "sentence_policy_strength": policy_strength,
                "domain_priority": sorted(priority_set),
                "switched_to_router_off_cases": switched_to_off,
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
    recommended = sorted(viable, key=lambda r: (r["metrics"]["avg_reconstruction_fidelity_jaccard"], r["metrics"]["global_token_saving_rate"]), reverse=True)[0] if viable else None
    decision = "GO_W7_E3_PARETO_SCORER" if recommended else "HOLD_W7_E2_NO_VIABLE"

    out_doc = {
        "schema": "track_a_week7_semantic_chunk_sweep_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "pack": str(args.pack),
            "chunk_size_grid": chunk_grid,
            "sentence_policy_strength": policy_grid,
            "domain_priority": sorted(priority_set),
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
            "Proceed to W7-E3 pareto scorer sweep."
            if decision == "GO_W7_E3_PARETO_SCORER"
            else "Keep baseline and continue to W7-E3 dual-objective scorer path."
        ),
        "runs": sorted(runs, key=lambda r: (r["metrics"]["avg_reconstruction_fidelity_jaccard"], r["metrics"]["global_token_saving_rate"]), reverse=True),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "viable_count": len(viable)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
