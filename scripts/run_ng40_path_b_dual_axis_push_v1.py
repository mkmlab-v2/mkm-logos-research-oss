#!/usr/bin/env python3
"""[HYPO] Path B push: 41k+ACTIVE-parity cap grid vs frozen ACTIVE (not shard parallel).

Finds configs where saving AND Jaccard both >= MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.
Writes ng40_latent_eval_path_b_best_v1_latest.json + refreshes promotion packet.
Does NOT run --apply-active.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    ACTIVE,
    INPUT_V2,
    _beat,
    _metrics,
    evaluate_ng40_lane,
)

OUT_BEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_best_v1_latest.json"
)
OUT_SWEEP = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_sweep_v1_latest.json"
)
OUT_MANIFEST = ROOT / "reports/ng40_path_b_dual_axis_push_v1_latest.json"

FROZEN_SAVING = 0.47538677918424754
FROZEN_J = 0.8904921794966301


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _live_active_on_disk() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    doc = json.loads(ACTIVE.read_text(encoding="utf-8-sig"))
    cm = doc.get("compression_metrics") or {}
    return {"present": True, **_metrics(cm)}


def _frozen_active() -> dict[str, Any]:
    """Canonical Track A gate — do not use drifted on-disk ACTIVE for beat_check."""
    live = _live_active_on_disk()
    if not live.get("present"):
        return {"present": False}
    return {
        "present": True,
        "case_count": live.get("case_count"),
        "global_token_saving_rate": FROZEN_SAVING,
        "avg_reconstruction_fidelity_jaccard": FROZEN_J,
        "min_reconstruction_fidelity_jaccard": live.get("min_reconstruction_fidelity_jaccard"),
        "sensitive_violation_count": live.get("sensitive_violation_count"),
        "beat_baseline": "canonical_frozen_constants",
    }


def _rank(row: dict[str, Any]) -> tuple:
    bc = row.get("beat_check") or {}
    agg = row.get("aggregate") or {}
    b = 1 if bc.get("beat_frozen") else 0
    j = float(agg.get("avg_reconstruction_fidelity_jaccard") or 0)
    s = float(agg.get("global_token_saving_rate") or 0)
    dj = float(bc.get("delta_jaccard_pp") or -999)
    ds = float(bc.get("delta_saving_pp") or -999)
    return (b, dj, ds, j, s)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--skip-promotion-packet", action="store_true")
    ap.add_argument(
        "--include-off-41k",
        action="store_true",
        help="Also sweep no-41k ultra-fine caps (usually below ACTIVE J)",
    )
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench_input"}))
        return 2

    frozen = _frozen_active()
    if not frozen.get("present"):
        print(json.dumps({"error": "missing_active_report"}))
        return 2

    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    baseline_j = 0.0
    baseline_path = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
    if baseline_path.is_file():
        bdoc = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
        baseline_j = float(
            bdoc.get("compression_metrics", {}).get(
                "avg_reconstruction_fidelity_jaccard", 0.0
            )
        )

    rows: list[dict[str, Any]] = []

    # 41k ON + ACTIVE parity — primary Path B lane (fair vs frozen ACTIVE).
    general_41k = (0.30, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37)
    sensitive_41k = (0.26, 0.28, 0.30, 0.32)
    hangul_41k = (0.50, 0.52, 0.55, 0.58, 0.60)
    relaxed_flags = (False, True)

    for g, s, h, relaxed in product(general_41k, sensitive_41k, hangul_41k, relaxed_flags):
        agg, _report = evaluate_ng40_lane(
            doc,
            bench_input=args.bench_input,
            general_cap=g,
            sensitive_cap=s,
            hangul_cap=h,
            baseline_j=baseline_j,
            use_domain_relaxed=relaxed,
            use_master_codebook_lexicon_v1=True,
            active_track_parity=True,
        )
        beat = _beat(agg, frozen)
        rows.append(
            {
                "lane": "41k_on_active_parity",
                "caps": {
                    "general_max_saving_rate": g,
                    "sensitive_max_saving_rate": s,
                    "hangul_max_saving_rate": h,
                    "with_domain_relaxed": relaxed,
                    "use_master_codebook_lexicon_v1": True,
                    "active_track_parity": True,
                },
                "aggregate": agg,
                "beat_check": beat,
            }
        )

    if args.include_off_41k:
        for g, s, h in product(
            (0.30, 0.31, 0.32, 0.33),
            (0.26, 0.27, 0.28),
            (0.52, 0.54, 0.56),
        ):
            agg, _report = evaluate_ng40_lane(
                doc,
                bench_input=args.bench_input,
                general_cap=g,
                sensitive_cap=s,
                hangul_cap=h,
                baseline_j=baseline_j,
                use_domain_relaxed=False,
                use_master_codebook_lexicon_v1=False,
                active_track_parity=False,
            )
            beat = _beat(agg, frozen)
            rows.append(
                {
                    "lane": "41k_off",
                    "caps": {
                        "general_max_saving_rate": g,
                        "sensitive_max_saving_rate": s,
                        "hangul_max_saving_rate": h,
                        "with_domain_relaxed": False,
                        "use_master_codebook_lexicon_v1": False,
                        "active_track_parity": False,
                    },
                    "aggregate": agg,
                    "beat_check": beat,
                }
            )

    rows.sort(key=_rank, reverse=True)
    any_beat = any((r.get("beat_check") or {}).get("beat_frozen") for r in rows)
    best = rows[0] if rows else None

    sweep_doc = {
        "schema": "ng40_path_b_dual_axis_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "frozen_active_reference": {
            "path": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
            "global_token_saving_rate": FROZEN_SAVING,
            "avg_reconstruction_fidelity_jaccard": FROZEN_J,
        },
        "combo_count": len(rows),
        "any_beat_frozen_vs_active": any_beat,
        "beat_rows_count": sum(
            1 for r in rows if (r.get("beat_check") or {}).get("beat_frozen")
        ),
        "rows": rows,
    }
    OUT_SWEEP.parent.mkdir(parents=True, exist_ok=True)
    OUT_SWEEP.write_text(
        json.dumps(sweep_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    best_doc: dict[str, Any] | None = None
    if best:
        caps = best.get("caps") or {}
        agg, report = evaluate_ng40_lane(
            doc,
            bench_input=args.bench_input,
            general_cap=float(caps.get("general_max_saving_rate", 0.35)),
            sensitive_cap=float(caps.get("sensitive_max_saving_rate", 0.28)),
            hangul_cap=float(caps.get("hangul_max_saving_rate", 0.55)),
            baseline_j=baseline_j,
            use_domain_relaxed=bool(caps.get("with_domain_relaxed")),
            use_master_codebook_lexicon_v1=bool(caps.get("use_master_codebook_lexicon_v1")),
            active_track_parity=bool(caps.get("active_track_parity")),
        )
        beat = _beat(agg, frozen)
        report_path = OUT_BEST.parent / f"{OUT_BEST.stem}.report.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        best_doc = {
            "schema": "nextgen_latent_eval_ng40_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypo_label": "[HYPO]",
            "track_a_active_write": False,
            "path_b_lane": True,
            "arm_id": "ng40_latent_eval_path_b_best_v1",
            "source_sweep": str(OUT_SWEEP.relative_to(ROOT)).replace("\\", "/"),
            "golden40_compatible": True,
            "lane": "path_b_41k_on_active_parity_cap_grid",
            "aggregate": agg,
            "frozen_baseline_active": frozen,
            "beat_check": beat,
            "run_config_summary": {**caps, "mode": "experimental"},
            "report_pointer": str(report_path.relative_to(ROOT)).replace("\\", "/"),
            "guardrails": [
                "beat_check uses ACTIVE report only (not shard merged parallel)",
                "export_prep_ready requires promotion packet + human gates",
                "No --apply-active from this script",
            ],
        }
        OUT_BEST.write_text(
            json.dumps(best_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    pkt_rc = 0
    if not args.skip_promotion_packet:
        pkt_rc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py"),
            ],
            cwd=str(ROOT),
            check=False,
        ).returncode

    live_active = _live_active_on_disk()
    manifest = {
        "schema": "ng40_path_b_dual_axis_push_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "beat_baseline": "canonical_frozen_constants",
        "live_active_on_disk": live_active,
        "any_beat_frozen_vs_active": any_beat,
        "best": {
            "path": str(OUT_BEST.relative_to(ROOT)).replace("\\", "/") if best_doc else None,
            "beat_frozen": (best_doc or {}).get("beat_check", {}).get("beat_frozen"),
            "saving": (best_doc or {}).get("aggregate", {}).get("global_token_saving_rate"),
            "jaccard": (best_doc or {}).get("aggregate", {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "caps": (best or {}).get("caps"),
        },
        "frozen_active": frozen,
        "sweep_pointer": str(OUT_SWEEP.relative_to(ROOT)).replace("\\", "/"),
        "promotion_packet_exit_code": pkt_rc,
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "wrote": str(OUT_MANIFEST),
                "any_beat": any_beat,
                "best_beat": (best_doc or {}).get("beat_check", {}).get("beat_frozen"),
                "combo_count": len(rows),
            },
            ensure_ascii=False,
        )
    )
    return 0 if pkt_rc == 0 else pkt_rc


if __name__ == "__main__":
    raise SystemExit(main())
