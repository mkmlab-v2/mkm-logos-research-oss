#!/usr/bin/env python3
"""[HYPO] Step 1: Golden-40 latent Path-B arms + verbatim/hybrid spine — single dual-KPI rollup."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_MANIFEST = ROOT / "reports/ng40_latent_spine_hybrid_eval_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DUAL_KPI = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_dual_kpi_harness_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:500]}
    return {
        "script": script,
        "args": extra or [],
        "exit_code": int(cp.returncode),
        "parsed": parsed,
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _latent_arm(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    agg = doc.get("aggregate") or {}
    beat = doc.get("beat_check") or {}
    return {
        "arm_id": doc.get("arm_id"),
        "lane": doc.get("lane"),
        "prior_terms_count": doc.get("prior_terms_count"),
        "saving": agg.get("global_token_saving_rate"),
        "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
        "beat_frozen": beat.get("beat_frozen"),
        "dual_axis": beat.get("beat_frozen"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-dual-kpi-run", action="store_true", help="Merge only existing JSON")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_dual_kpi_run:
        steps.append(
            _run(
                "scripts/run_nextgen_dual_kpi_harness_v1.py",
                ["--run-hybrid"],
            )
        )
        if steps[-1]["exit_code"] != 0:
            return steps[-1]["exit_code"]
    steps.append(_run("scripts/run_ng40_path_b_prior_41k_eval_v1.py"))
    steps.append(_run("scripts/run_ng40_path_b_trilane_prior_41k_eval_v1.py"))

    frozen_cm: dict[str, Any] = {}
    if ACTIVE.is_file():
        cm = json.loads(ACTIVE.read_text(encoding="utf-8-sig")).get("compression_metrics") or {}
        frozen_cm = {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        }

    dual = _load(str(DUAL_KPI.relative_to(ROOT)).replace("\\", "/"))
    latent_arms = {
        "path_b_archetype_prior_41k": _latent_arm(
            _load(
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_path_b_prior_41k_v1_latest.json"
            )
        ),
        "path_b_trilane_prior_41k": _latent_arm(
            _load(
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_path_b_trilane_prior_41k_v1_latest.json"
            )
        ),
    }
    any_latent_beat = any((a or {}).get("beat_frozen") for a in latent_arms.values())

    manifest = {
        "schema": "ng40_latent_spine_hybrid_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "frozen_active": frozen_cm,
        "dual_kpi_pointer": str(DUAL_KPI.relative_to(ROOT)).replace("\\", "/"),
        "dual_kpi_arms_summary": (dual or {}).get("arms_summary"),
        "pareto_rollup": {
            "both_axes_met": (dual or {}).get("both_axes_met_arms"),
            "byte_exact_only": (dual or {}).get("byte_exact_only_arms"),
        },
        "latent_path_b_arms": latent_arms,
        "any_latent_dual_axis_beat": any_latent_beat,
        "conclusion_ko": (
            "spine/hybrid 레인=byte_exact; latent Path-B=J·saving 분리 보고. "
            "ACTIVE 교체는 latent beat 없으면 금지."
        ),
        "steps": steps,
        "forbidden": ["collapse_latent_saving_into_spine_headline", "--apply-active"],
    }

    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(OUT_MANIFEST),
                "any_latent_dual_axis_beat": any_latent_beat,
                "dual_kpi_arms": len((dual or {}).get("arms_summary") or []),
            },
            ensure_ascii=False,
        )
    )
    hard = any(
        s["exit_code"] != 0
        for s in steps
        if s.get("script") == "scripts/run_nextgen_dual_kpi_harness_v1.py"
    )
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
