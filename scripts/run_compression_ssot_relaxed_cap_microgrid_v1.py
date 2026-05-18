#!/usr/bin/env python3
"""B-track: ssot relaxed-cap microgrid — floor vs min-Jaccard Pareto (RQ-016 A-plan phase 2).

Writes only ``compression_ssot_relaxed_cap_microgrid_v1_latest.json``.
Never touches Track A active report.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_ssot_relaxed_cap_microgrid_v1_latest.json"
POLICY_FLOOR = 0.47
SSOT_DOMAIN = "ssot"
REGRESSION_WATCH_IDS = frozenset({"cmp2_003", "cmp2_005", "cmp2_008", "cmp2_010"})

FORBIDDEN_WRITE = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json").resolve(),
    }
)

CAP_GRID = [0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_safe_out(path: Path) -> Path:
    if path.resolve() in FORBIDDEN_WRITE:
        raise SystemExit(f"Refusing to write Track A active report: {path}")
    return path


def _case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(c.get("id", "")): c for c in (report.get("compression_metrics") or {}).get("cases") or []}


def _metrics(
    report: dict[str, Any],
    *,
    track_a_min_j: float,
    ref_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    min_j = float(cm.get("min_reconstruction_fidelity_jaccard") or 0)
    pin_map = _case_map(report)
    regressions: list[dict[str, Any]] = []
    watch: list[dict[str, Any]] = []
    for cid, p in pin_map.items():
        r = ref_map.get(cid) or {}
        rj = r.get("reconstruction_fidelity_jaccard")
        pj = p.get("reconstruction_fidelity_jaccard")
        if rj is None or pj is None:
            continue
        dj = float(pj) - float(rj)
        if dj < -1e-9:
            regressions.append({"id": cid, "delta_jaccard": round(dj, 6), "jaccard_pin": pj})
        if cid in REGRESSION_WATCH_IDS:
            watch.append({"id": cid, "delta_jaccard": round(dj, 6), "jaccard_pin": pj})
    return {
        "global_token_saving_rate": saving,
        "distance_to_policy_floor": round(abs(saving - POLICY_FLOOR), 6),
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": min_j,
        "min_jaccard_not_below_track_a": min_j >= track_a_min_j - 1e-9,
        "cases_with_jaccard_regression_count": len(regressions),
        "regression_watch_cases": watch,
    }


def _rank_key(row: dict[str, Any]) -> tuple:
    """Prefer: floor+min_j ok, fewer regressions, higher saving, higher min_j."""
    floor = 1 if row.get("ultra_saving_policy_ok") else 0
    min_ok = 1 if row.get("min_jaccard_not_below_track_a") else 0
    reg = -int(row.get("cases_with_jaccard_regression_count") or 0)
    saving = float(row.get("global_token_saving_rate") or 0)
    min_j = float(row.get("min_reconstruction_fidelity_jaccard") or 0)
    return (min_ok, floor, reg, saving, min_j)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_path = _assert_safe_out(args.out_json)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "cap_grid": CAP_GRID,
                    "out_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    ta = _load(TRACK_A_ACTIVE)
    tacm = ta.get("compression_metrics") or {}
    track_a_min_j = float(tacm.get("min_reconstruction_fidelity_jaccard") or 0)
    track_a_saving = float(tacm.get("global_token_saving_rate") or 0)
    ref_map = _case_map(ta)

    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    def _gms(x: Any) -> float | None:
        return float(x) if x is not None else None

    common = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(sel.get("strategy", "A")),
        intensity=str(sel.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_gms(sel.get("general_max_saving_rate")),
        sensitive_max_saving_rate=_gms(sel.get("sensitive_max_saving_rate")),
        hangul_max_saving_rate=_gms(sel.get("hangul_max_saving_rate")),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=False,
    )

    results: list[dict[str, Any]] = []
    for cap in CAP_GRID:
        rep = evaluate_report(
            src,
            **common,
            domain_relaxed_max_saving_overrides={SSOT_DOMAIN: cap},
        )
        m = _metrics(rep, track_a_min_j=track_a_min_j, ref_map=ref_map)
        results.append(
            {
                "id": f"ssot_relaxed_cap_{cap:.2f}".replace(".", "_"),
                "ssot_relaxed_cap": cap,
                "delta_global_saving_vs_track_a": round(m["global_token_saving_rate"] - track_a_saving, 6),
                **m,
            }
        )

    joint_pass = [
        r
        for r in results
        if r.get("ultra_saving_policy_ok") and r.get("min_jaccard_not_below_track_a")
    ]
    floor_only = [r for r in results if r.get("ultra_saving_policy_ok")]
    ranked = sorted(results, key=_rank_key, reverse=True)

    doc = {
        "schema": "compression_ssot_relaxed_cap_microgrid_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016-A-plan-phase2",
        "policy_floor": POLICY_FLOOR,
        "cap_grid": CAP_GRID,
        "track_a_reference_readonly": {
            "global_token_saving_rate": track_a_saving,
            "min_reconstruction_fidelity_jaccard": track_a_min_j,
        },
        "regression_watch_ids": sorted(REGRESSION_WATCH_IDS),
        "grid_size": len(results),
        "floor_pass_count": len(floor_only),
        "joint_floor_and_min_j_pass_count": len(joint_pass),
        "best_joint_pass": joint_pass[0] if joint_pass else None,
        "best_by_rank": ranked[0] if ranked else None,
        "top3_by_rank": ranked[:3],
        "all_rows": results,
        "key_finding": (
            "No cap in grid achieves floor>=0.47 AND min_j>=track_a simultaneously"
            if not joint_pass
            else f"joint pass at cap={joint_pass[0].get('ssot_relaxed_cap')}"
        ),
        "promotion_note": "Does not replace MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "joint_pass_count": len(joint_pass),
                "best_id": ranked[0].get("id") if ranked else None,
                "key_finding": doc["key_finding"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
