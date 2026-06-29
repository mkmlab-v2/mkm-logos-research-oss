#!/usr/bin/env python3
"""B-track compression pipeline grid sweep — Golden-40, isolated from Track A active write.

Runs evaluate_report cells under experiments/compression_pipeline_grid_sweep_v1/ and compares
each to the frozen MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json (read-only).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
)
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_ultra_compression_default import (  # noqa: E402
    BASELINE_V2,
    DECISION,
    INPUT_V2,
)
from scripts.ultra_compression_track_a_policy_floor_v1 import (  # noqa: E402
    apply_promoted_policy_floor_to_quality_gate,
)

EXP = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1"
MANIFEST = EXP / "grid_manifest_v1.json"
RUNS = EXP / "runs"
RESULTS = EXP / "results"
PILOT_MIRROR = ROOT / "reports" / "constitution" / "btrack_pilot"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_LEXICON = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "master_codebook_lexicon_v1_41708_rows_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _per_case_delta(
    baseline_cases: list[dict[str, Any]], candidate_cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_b = {str(c.get("id")): c for c in baseline_cases if c.get("id")}
    by_c = {str(c.get("id")): c for c in candidate_cases if c.get("id")}
    out: list[dict[str, Any]] = []
    for cid in sorted(set(by_b) & set(by_c)):
        b, c = by_b[cid], by_c[cid]
        ds = float(c.get("token_saving_rate") or 0) - float(b.get("token_saving_rate") or 0)
        dj = float(c.get("reconstruction_fidelity_jaccard") or 0) - float(
            b.get("reconstruction_fidelity_jaccard") or 0
        )
        out.append(
            {
                "id": cid,
                "frozen_active_saving": round(float(b.get("token_saving_rate") or 0), 6),
                "candidate_saving": round(float(c.get("token_saving_rate") or 0), 6),
                "delta_saving": round(ds, 6),
                "frozen_active_jaccard": round(float(b.get("reconstruction_fidelity_jaccard") or 0), 6),
                "candidate_jaccard": round(float(c.get("reconstruction_fidelity_jaccard") or 0), 6),
                "delta_jaccard": round(dj, 6),
            }
        )
    return out


def _run_sla_track_subprocess(mode: str, out_path: Path) -> tuple[int, dict[str, Any] | None]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_ultra_compression_default.py"),
        "--mode",
        mode,
        "--out",
        str(out_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = ((proc.stdout or "") + (proc.stderr or ""))[-800:]
        return proc.returncode, {"error_tail": tail}
    if not out_path.is_file():
        return 2, {"error": "missing output after subprocess"}
    return 0, _load_json(out_path)


def _eval_profile_cell(
    src: dict[str, Any],
    profile: str,
    lexicon: Path,
    domain_relaxed: dict[str, float],
    allow: frozenset[str] | None,
    exclude: frozenset[str] | None,
) -> dict[str, Any]:
    baseline_doc = _load_json(BASELINE_V2)
    decision_doc = _load_json(DECISION)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    kw = profile_evaluate_report_kwargs(profile)  # type: ignore[arg-type]
    report = evaluate_report(
        src,
        source_input=_rel(INPUT_V2),
        mode="experimental",
        must_keep={"사상의학", "체질", "sasang", "myeongni", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        master_codebook_lexicon_path=str(lexicon.resolve()),
        domain_relaxed_max_saving_overrides=domain_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=allow,
        domain_relaxed_max_saving_exclude_case_ids=exclude,
        **kw,
    )
    if profile == "economy":
        apply_promoted_policy_floor_to_quality_gate(report)
    return report



def _gate_cell(
    cell_metrics: dict[str, Any],
    frozen_metrics: dict[str, Any],
    *,
    max_jaccard_drop_pp: float,
    require_sensitive_zero: bool,
) -> dict[str, Any]:
    fj = float(frozen_metrics.get("avg_reconstruction_fidelity_jaccard") or 0)
    cj = float(cell_metrics.get("avg_reconstruction_fidelity_jaccard") or 0)
    fs = float(frozen_metrics.get("global_token_saving_rate") or 0)
    cs = float(cell_metrics.get("global_token_saving_rate") or 0)
    dj_pp = (cj - fj) * 100.0
    ds_pp = (cs - fs) * 100.0
    sens = int(cell_metrics.get("sensitive_violation_count") or 0)
    floor_ok = dj_pp >= -max_jaccard_drop_pp
    sens_ok = sens == 0 if require_sensitive_zero else True
    beat_both = cs >= fs and cj >= fj
    return {
        "delta_saving_pp": round(ds_pp, 4),
        "delta_jaccard_pp": round(dj_pp, 4),
        "floor_ok": floor_ok,
        "sensitive_ok": sens_ok,
        "beat_frozen_both_axes": beat_both,
        "passes_experiment_gate": floor_ok and sens_ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track compression pipeline grid sweep (no active write).")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument(
        "--out-summary",
        type=Path,
        default=RESULTS / "compression_pipeline_grid_sweep_v1_latest.json",
    )
    ap.add_argument(
        "--out-diff",
        type=Path,
        default=RESULTS / "compression_pipeline_grid_sweep_golden40_diff_v1_latest.json",
    )
    ap.add_argument("--mirror-pilot", action="store_true", help="Also write summary under btrack_pilot/")
    ap.add_argument("--include-cost-sim", action="store_true", help="Run cost sim (baseline-linked only).")
    ap.add_argument("--skip-sla-modes", action="store_true")
    ap.add_argument("--skip-profiles", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"ABORT: missing manifest {manifest_path}")
        return 2
    if not ACTIVE.is_file() or not INPUT_V2.is_file():
        print("ABORT: missing frozen active report or V2 bench input")
        return 2

    manifest = _load_json(manifest_path)
    lexicon = Path(args.lexicon)
    if not lexicon.is_file():
        print(f"ABORT: missing lexicon {lexicon}")
        return 2

    gates = manifest.get("gates") or {}
    max_j_pp = float(gates.get("max_jaccard_drop_pp_vs_frozen_active", 2.0))
    require_sens = bool(gates.get("require_sensitive_violation_zero", True))

    frozen_doc = _load_json(ACTIVE)
    frozen_metrics = _metrics(frozen_doc)
    frozen_cases = (frozen_doc.get("compression_metrics") or {}).get("cases") or []

    if args.dry_run:
        print(f"DRY-RUN manifest={_rel(manifest_path)} frozen={_rel(ACTIVE)}")
        print(f"  sla_modes={manifest.get('sla_track_modes')} profiles={manifest.get('compression_profiles')}")
        return 0

    RUNS.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    cells: list[dict[str, Any]] = []
    diff_by_cell: dict[str, list[dict[str, Any]]] = {}

    if not args.skip_sla_modes:
        for mode in manifest.get("sla_track_modes") or []:
            mode = str(mode)
            run_out = RUNS / f"sla_{mode.replace('-', '_')}.json"
            code, doc = _run_sla_track_subprocess(mode, run_out)
            if code != 0 or doc is None:
                cells.append(
                    {
                        "cell_id": f"sla_{mode}",
                        "kind": "sla_track",
                        "mode": mode,
                        "exit_code": code,
                        "error": doc,
                    }
                )
                continue
            m = _metrics(doc)
            g = _gate_cell(m, frozen_metrics, max_jaccard_drop_pp=max_j_pp, require_sensitive_zero=require_sens)
            cases = (doc.get("compression_metrics") or {}).get("cases") or []
            pcd = _per_case_delta(frozen_cases, cases)
            cells.append(
                {
                    "cell_id": f"sla_{mode}",
                    "kind": "sla_track",
                    "mode": mode,
                    "report_path": _rel(run_out),
                    "metrics": m,
                    "gate": g,
                }
            )
            diff_by_cell[f"sla_{mode}"] = pcd

    if not args.skip_profiles:
        src = _load_json(INPUT_V2)
        relaxed, allow, exclude = _load_signoff_relaxed()
        for profile in manifest.get("compression_profiles") or []:
            profile = str(profile)
            report = _eval_profile_cell(src, profile, lexicon, relaxed, allow, exclude)
            run_out = RUNS / f"profile_{profile}.json"
            run_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            m = _metrics(report)
            g = _gate_cell(m, frozen_metrics, max_jaccard_drop_pp=max_j_pp, require_sensitive_zero=require_sens)
            cases = (report.get("compression_metrics") or {}).get("cases") or []
            pcd = _per_case_delta(frozen_cases, cases)
            cells.append(
                {
                    "cell_id": f"profile_{profile}",
                    "kind": "compression_profile",
                    "profile": profile,
                    "report_path": _rel(run_out),
                    "metrics": m,
                    "gate": g,
                }
            )
            diff_by_cell[f"profile_{profile}"] = pcd

    cost_sim_pointer: str | None = None
    if args.include_cost_sim:
        cost_out = RESULTS / "track_a_conversational_cost_simulation_baseline_linked.json"
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_track_a_conversational_cost_simulation.py"),
            "--workspace-root",
            str(ROOT),
            "--active-report",
            str(ACTIVE),
            "--out",
            str(cost_out),
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            cost_sim_pointer = _rel(cost_out)

    beat_cells = [
        c["cell_id"]
        for c in cells
        if c.get("gate", {}).get("beat_frozen_both_axes") and c.get("gate", {}).get("passes_experiment_gate")
    ]

    summary = {
        "schema": "compression_pipeline_grid_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "correlation_claim_allowed": False,
        "manifest_path": _rel(manifest_path),
        "bench_input": _rel(INPUT_V2),
        "frozen_baseline": {
            "pointer": _rel(ACTIVE),
            "metrics": frozen_metrics,
            "note": "Read-only reference; this sweep does not overwrite active report.",
        },
        "cells": cells,
        "cost_sim_baseline_linked": cost_sim_pointer,
        "verdict": {
            "promote_active": False,
            "beat_frozen_cells": beat_cells,
            "beat_frozen_count": len(beat_cells),
            "recommendation": (
                "Experiment gate only. Human sign-off required before any active report change."
                if beat_cells
                else "No cell beat frozen active on both saving and Jaccard; pipeline overhaul TBD."
            ),
        },
        "guardrails": manifest.get("forbidden"),
    }

    diff_doc = {
        "schema": "compression_pipeline_grid_sweep_golden40_diff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "frozen_baseline_pointer": _rel(ACTIVE),
        "cells": diff_by_cell,
    }

    out_summary = Path(args.out_summary)
    out_diff = Path(args.out_diff)
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_diff.write_text(json.dumps(diff_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.mirror_pilot:
        PILOT_MIRROR.mkdir(parents=True, exist_ok=True)
        mirror = PILOT_MIRROR / "compression_pipeline_grid_sweep_v1_latest.json"
        mirror.write_text(out_summary.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"WROTE: {out_summary}")
    print(f"WROTE: {out_diff}")
    print(f"cells={len(cells)} beat_frozen={len(beat_cells)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
