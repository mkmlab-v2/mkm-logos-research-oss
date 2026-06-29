#!/usr/bin/env python3
"""[HYPO] Decompose Path B dual-axis sweep vs canonical frozen ACTIVE."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SWEEP_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_sweep_v1_latest.json"
)
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = ROOT / "reports/ng40_path_b_dual_axis_beat_decomposition_v1_latest.json"

CANON_S = 0.47538677918424754
CANON_J = 0.8904921794966301


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _live_active() -> dict[str, float]:
    if not ACTIVE.is_file():
        return {}
    doc = json.loads(ACTIVE.read_text(encoding="utf-8-sig"))
    cm = doc.get("compression_metrics") or {}
    return {
        "saving": float(cm.get("global_token_saving_rate", 0)),
        "jaccard": float(cm.get("avg_reconstruction_fidelity_jaccard", 0)),
    }


def _beat(agg: dict[str, Any], s_f: float, j_f: float) -> tuple[bool, float, float]:
    s_c = float(agg.get("global_token_saving_rate", 0))
    j_c = float(agg.get("avg_reconstruction_fidelity_jaccard", 0))
    return (
        s_c >= s_f and j_c >= j_f,
        round((s_c - s_f) * 100, 2),
        round((j_c - j_f) * 100, 2),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    if not args.sweep_json.is_file():
        print(json.dumps({"error": "missing_sweep", "path": str(args.sweep_json)}))
        return 2

    sweep = json.loads(args.sweep_json.read_text(encoding="utf-8-sig"))
    rows = sweep.get("rows") or []
    live = _live_active()

    canon_dual = j_only = s_only = neither = 0
    live_dual = 0
    best_j_row: dict[str, Any] | None = None
    best_s_row: dict[str, Any] | None = None

    for r in rows:
        agg = r.get("aggregate") or {}
        b, ds, dj = _beat(agg, CANON_S, CANON_J)
        s_c = float(agg.get("global_token_saving_rate", 0))
        j_c = float(agg.get("avg_reconstruction_fidelity_jaccard", 0))
        if b:
            canon_dual += 1
        elif j_c >= CANON_J and s_c < CANON_S:
            j_only += 1
        elif s_c >= CANON_S and j_c < CANON_J:
            s_only += 1
        else:
            neither += 1
        if live:
            if _beat(agg, live["saving"], live["jaccard"])[0]:
                live_dual += 1
        if best_j_row is None or j_c > float(
            (best_j_row.get("aggregate") or {}).get("avg_reconstruction_fidelity_jaccard", 0)
        ):
            best_j_row = r
        if best_s_row is None or s_c > float(
            (best_s_row.get("aggregate") or {}).get("global_token_saving_rate", 0)
        ):
            best_s_row = r

    def _arm_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        agg = row.get("aggregate") or {}
        _, ds, dj = _beat(agg, CANON_S, CANON_J)
        return {
            "caps": row.get("caps"),
            "lane": row.get("lane"),
            "saving": agg.get("global_token_saving_rate"),
            "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
            "delta_vs_canon_pp": {"saving": ds, "jaccard": dj},
        }

    out = {
        "schema": "ng40_path_b_dual_axis_beat_decomposition_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "sweep_pointer": str(args.sweep_json.relative_to(ROOT)).replace("\\", "/"),
        "canonical_frozen_active": {
            "saving": CANON_S,
            "jaccard": CANON_J,
            "source": "canonical_frozen_constants",
        },
        "live_active_on_disk": {
            **live,
            "path": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
            "drift_vs_canonical_pp": {
                "saving": round((live.get("saving", 0) - CANON_S) * 100, 2) if live else None,
                "jaccard": round((live.get("jaccard", 0) - CANON_J) * 100, 2) if live else None,
            },
        },
        "sweep_combo_count": len(rows),
        "vs_canonical_frozen": {
            "dual_axis_beat_count": canon_dual,
            "j_only_better": j_only,
            "s_only_better": s_only,
            "neither": neither,
        },
        "vs_live_active_disk": {
            "dual_axis_beat_count": live_dual,
            "note": "live ACTIVE drift can inflate beat count if used as beat baseline",
        },
        "best_by_jaccard": _arm_summary(best_j_row),
        "best_by_saving": _arm_summary(best_s_row),
        "structural_read": (
            "Jaccard uplift arms trade saving below canonical frozen; "
            "saving-high arms collapse Jaccard — Pareto gap under 41k+ACTIVE-parity grid."
        ),
        "promotion": {
            "apply_forbidden": True,
            "active_overwrite": False,
            "reason": "canonical dual-axis beat false unless count > 0",
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "canon_dual": canon_dual,
                "live_dual": live_dual,
                "combo_count": len(rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
