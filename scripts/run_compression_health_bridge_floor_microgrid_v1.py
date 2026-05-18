#!/usr/bin/env python3
"""Health-only bridge weight micro-sweep near policy floor 0.47 (RQ-016).

Writes only to ``compression_health_bridge_floor_microgrid_v1_latest.json``.
Never touches ``MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json``.
"""

from __future__ import annotations

import argparse
import itertools
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
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_health_bridge_floor_microgrid_v1_latest.json"
POLICY_FLOOR = 0.47
HEALTH_ID = "cmp2_014"
HEALTH_JACCARD_TARGET = 1.0

FORBIDDEN_WRITE = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json").resolve(),
    }
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_safe_out(path: Path) -> Path:
    resolved = path.resolve()
    if resolved in FORBIDDEN_WRITE:
        raise SystemExit(f"Refusing to write Track A active report: {path}")
    return resolved


def _track_a_readonly() -> dict[str, Any] | None:
    if not TRACK_A_ACTIVE.is_file():
        return None
    ta = _load(TRACK_A_ACTIVE)
    tacm = ta.get("compression_metrics") or {}
    health_row = next(
        (c for c in (tacm.get("cases") or []) if str(c.get("id", "")) == HEALTH_ID),
        None,
    )
    return {
        "path": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "global_token_saving_rate": tacm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": tacm.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": tacm.get("min_reconstruction_fidelity_jaccard"),
        "apply_gematria_4d_bridge_policy": (ta.get("run_config") or {}).get(
            "apply_gematria_4d_bridge_policy"
        ),
        "bridge_policy_domain_allowlist": (ta.get("run_config") or {}).get(
            "bridge_policy_domain_allowlist"
        ),
        "health_case": (
            {
                "id": HEALTH_ID,
                "jaccard": health_row.get("reconstruction_fidelity_jaccard"),
                "token_saving_rate": health_row.get("token_saving_rate"),
            }
            if health_row
            else None
        ),
    }


def _row_metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    avg_j = float(cm.get("avg_reconstruction_fidelity_jaccard") or 0)
    health_row = next(
        (c for c in (cm.get("cases") or []) if str(c.get("id", "")) == HEALTH_ID),
        None,
    )
    health_j = (
        float(health_row.get("reconstruction_fidelity_jaccard") or 0) if health_row else None
    )
    return {
        "global_token_saving_rate": saving,
        "distance_to_policy_floor": round(abs(saving - POLICY_FLOOR), 6),
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "avg_reconstruction_fidelity_jaccard": avg_j,
        "health_jaccard": health_j,
        "health_jaccard_ok": health_j is not None and health_j >= HEALTH_JACCARD_TARGET - 1e-9,
    }


def _rank_key(row: dict[str, Any]) -> tuple:
    """Floor pass first, then higher saving, then closer to floor, then avg jaccard."""
    floor = 1 if row.get("ultra_saving_policy_ok") else 0
    saving = float(row.get("global_token_saving_rate") or 0)
    dist = float(row.get("distance_to_policy_floor") or 999)
    return (
        floor,
        saving,
        -dist,
        float(row.get("avg_reconstruction_fidelity_jaccard") or 0),
    )


def _rank_key_near_floor(row: dict[str, Any]) -> tuple:
    """Among floor+health-jaccard rows: closest to policy floor, then higher saving."""
    dist = float(row.get("distance_to_policy_floor") or 999)
    saving = float(row.get("global_token_saving_rate") or 0)
    return (-dist if row.get("ultra_saving_policy_ok") else -999, -dist, saving)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-json",
        type=Path,
        default=OUT_DEFAULT,
        help=f"Output path (default B-track microgrid artifact). Track A path rejected.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config and paths only; do not evaluate or write.",
    )
    args = ap.parse_args()
    out_path = _assert_safe_out(args.out_json)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "out_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                    "track_a_active_read_only": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace(
                        "\\", "/"
                    ),
                    "policy_floor": POLICY_FLOOR,
                    "health_case_id": HEALTH_ID,
                },
                ensure_ascii=False,
            )
        )
        return 0

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
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
    )

    grid_fixed = {"guard": 0.4, "distance_penalty": 1.5}
    grid = {
        "saving": [0.7, 0.75, 0.8, 0.85, 0.9, 0.95],
        "fidelity": [0.95, 1.0, 1.05],
    }

    results: list[dict[str, Any]] = []
    for f, s in itertools.product(grid["fidelity"], grid["saving"]):
        weights = {"fidelity": f, "guard": grid_fixed["guard"], "saving": s, "distance_penalty": grid_fixed["distance_penalty"]}
        rep = evaluate_report(
            src,
            **common,
            apply_gematria_4d_bridge_policy=True,
            bridge_policy_domain_allowlist=frozenset({"health"}),
            bridge_score_weights=weights,
        )
        m = _row_metrics(rep)
        results.append(
            {
                "id": f"health_w_f{f}_s{s}_g{grid_fixed['guard']}_d{grid_fixed['distance_penalty']}",
                "weights": weights,
                "allowlist": ["health"],
                **m,
            }
        )

    eligible = [r for r in results if r.get("health_jaccard_ok")]
    ranked = sorted(eligible, key=_rank_key, reverse=True)
    floor_pass = [r for r in eligible if r.get("ultra_saving_policy_ok")]
    best_by_saving = floor_pass[0] if floor_pass else (ranked[0] if ranked else None)
    near_floor = sorted(
        [r for r in floor_pass if r.get("health_jaccard_ok")],
        key=_rank_key_near_floor,
        reverse=True,
    )
    best_near_floor = near_floor[0] if near_floor else None

    doc = {
        "schema": "compression_health_bridge_floor_microgrid_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016",
        "policy_floor": POLICY_FLOOR,
        "health_case_id": HEALTH_ID,
        "health_jaccard_target": HEALTH_JACCARD_TARGET,
        "grid": {**grid, **grid_fixed},
        "bridge_policy_domain_allowlist": ["health"],
        "apply_gematria_4d_bridge_policy": True,
        "track_a_reference_readonly": _track_a_readonly(),
        "grid_size": len(results),
        "health_jaccard_ok_count": len(eligible),
        "floor_pass_count": len(floor_pass),
        "best_by_saving_floor_pass_first": best_by_saving,
        "best_near_policy_floor_health_jaccard_ok": best_near_floor,
        "top5_by_rank": ranked[:5],
        "all_rows": results,
        "promotion_note": (
            "Does not replace MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json. "
            "Health allowlist microgrid only."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "grid_size": doc["grid_size"],
                "health_jaccard_ok_count": doc["health_jaccard_ok_count"],
                "floor_pass_count": doc["floor_pass_count"],
                "best_id": (best_by_saving or {}).get("id"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
