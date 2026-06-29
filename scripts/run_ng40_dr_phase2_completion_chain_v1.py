#!/usr/bin/env python3
"""[HYPO] DR Phase 2 completion — B2B expand + Ollama shadow + Path A signoff refresh.

research_only · send_gate HOLD · never --apply-active.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/ng40_dr_phase2_completion_chain_v1_latest.json"
LONGFORM_EXPANDED = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_LONGFORM_SPINE_BENCH_EXPANDED_V1.json"
)
SPINE_EXPANDED_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_expanded_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-b2b-expand", action="store_true")
    ap.add_argument("--skip-ollama-shadow", action="store_true")
    ap.add_argument("--skip-microgrid", action="store_true")
    ap.add_argument("--skip-path-a-signoff", action="store_true")
    ap.add_argument("--skip-golden40-dual", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_b2b_expand:
        steps.append(
            _run(
                "build_longform_expanded",
                [
                    PY,
                    "scripts/build_nextgen_longform_spine_bench_input_v1.py",
                    "--max-cases",
                    "120",
                    "--min-raw-bytes",
                    "512",
                    "--out-json",
                    str(LONGFORM_EXPANDED.resolve()),
                ],
            )
        )
        steps.append(
            _run(
                "spine_binary_billable_expanded",
                [
                    PY,
                    "scripts/run_nextgen_spine_binary_billable_eval_v1.py",
                    "--bench-input",
                    str(LONGFORM_EXPANDED.resolve()),
                    "--out-json",
                    str(SPINE_EXPANDED_EVAL.resolve()),
                    "--arm-id",
                    "ng40_spine_binary_billable_expanded_v1",
                    "--bench-label",
                    "b2b_longform_expanded",
                ],
            )
        )

    if not args.skip_ollama_shadow:
        steps.append(_run("ollama_open_bench_shadow", [PY, "scripts/run_compression_ollama_open_bench_shadow_v1.py"]))

    if not args.skip_microgrid:
        steps.append(_run("path_a_keep_ratio_microgrid", [PY, "scripts/run_ng40_path_a_keep_ratio_microgrid_v1.py"]))

    if not args.skip_path_a_signoff:
        steps.append(
            _run(
                "path_a_product_signoff",
                [PY, "scripts/run_ng40_path_a_product_signoff_chain_v1.py", "--skip-auto-ops"],
            )
        )

    if not args.skip_golden40_dual:
        steps.append(
            _run("golden40_active_dual_report", [PY, "scripts/build_compression_golden40_active_dual_report_v1.py"])
        )

    failed = [s for s in steps if s["exit_code"] != 0]
    microgrid = _load("reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json")
    signoff = _load("reports/ng40_path_a_product_signoff_chain_v1_latest.json")
    shadow = _load("reports/compression_ollama_shadow_dual_report_v1_latest.json")
    expanded = _load(str(SPINE_EXPANDED_EVAL.relative_to(ROOT)).replace("\\", "/")) if SPINE_EXPANDED_EVAL.is_file() else None

    spine_headline = None
    if microgrid:
        rec = microgrid.get("recommendation") or {}
        b2b = (microgrid.get("b2b_longform") or {}).get("canonical_keep_0.88") or {}
        spine_headline = b2b.get("global_token_saving_rate_spine_binary_only") or rec.get("product_headline_spine_saving")

    doc: dict[str, Any] = {
        "schema": "ng40_dr_phase2_completion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "chain_ok": len(failed) == 0,
        "failed_steps": [s["id"] for s in failed],
        "steps": steps,
        "headlines": {
            "product_spine_saving_invariant": spine_headline,
            "product_ready": (signoff or {}).get("product_gates", {}).get("product_ready"),
            "canonical_keep_ratio": (signoff or {}).get("canonical_keep_ratio"),
            "expanded_b2b_case_count": (expanded or {}).get("aggregate", {}).get("case_count"),
            "expanded_spine_saving": (expanded or {}).get("aggregate", {}).get(
                "global_token_saving_rate_spine_binary_billable"
            ),
            "open_bench_non_zero_cohorts": (shadow or {}).get("summary", {}).get("open_bench_non_zero_saving"),
        },
        "four_lane_decoupling_ko": {
            "latent_research": "~47% evaluate_report — Track A competitor, no dual beat",
            "product_b2b": f"spine ~{round(float(spine_headline or 0)*100, 2)}% byte_exact — commercial honest KPI",
            "ollama_hero": "routing/inject — not compression engine",
            "ur_topology": "99.53% symbolic — NON_GATING",
        },
        "pointers": {
            "microgrid": "reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json",
            "ollama_shadow": "reports/compression_ollama_shadow_dual_report_v1_latest.json",
            "path_a_signoff": "reports/ng40_path_a_product_signoff_chain_v1_latest.json",
            "golden40_dual": "reports/compression_golden40_active_dual_report_v1_latest.json",
            "expanded_spine_eval": str(SPINE_EXPANDED_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "dr_lit_review": "docs/research/COMPRESSION_IMPROVEMENT_OLLAMA_THEORY_BEST_PATH_LIT_REVIEW_2026-06-22.md",
        },
        "reproducible_command": "py scripts/run_ng40_dr_phase2_completion_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": doc["chain_ok"], "failed_steps": doc["failed_steps"]}, ensure_ascii=False))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
