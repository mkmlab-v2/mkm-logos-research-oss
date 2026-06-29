#!/usr/bin/env python3
"""Phase-2 orchestrator: field graph · lens routers · ablation · premium attach."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 300) -> dict:
    cp = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    return {"step": name, "exit_code": cp.returncode, "tail": ((cp.stdout or "") + (cp.stderr or "")).strip()[-600:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-premium", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    # Phase 1: base four-lens fusion
    steps.append(_run("run_four_lens_fusion_chain", [PY, "scripts/run_kospi_four_lens_graphrag_fusion_chain_v1.py", "--skip-lens-refresh"]))

    steps.append(_run("build_field_event_graph", [PY, "scripts/build_field_kospi_event_graph_v1.py"]))

    for lid, seed, lens, out in (
        (
            "myeongni",
            "data/btrack/lens_graphrag/kospi_tail_myeongni_hypo_v1.seed.json",
            "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "reports/btrack_lens_graphrag_myeongni_kospi_tail_v1_latest.json",
        ),
        (
            "sasang",
            "data/btrack/lens_graphrag/kospi_tail_sasang_hypo_v1.seed.json",
            "docs/final/artifacts/sasang_independent_lens_latest.json",
            "reports/btrack_lens_graphrag_sasang_kospi_tail_v1_latest.json",
        ),
    ):
        steps.append(
            _run(
                f"build_lens_router_{lid}",
                [
                    PY,
                    "scripts/build_btrack_lens_graphrag_router_slice_v1.py",
                    "--seed",
                    seed,
                    "--lens-json",
                    lens,
                    "--output-json",
                    out,
                ],
            )
        )

    steps.append(_run("rebuild_four_lens_fusion", [PY, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py"]))
    steps.append(_run("conditional_fusion_ablation", [PY, "scripts/run_kospi_four_lens_conditional_fusion_ablation_v1.py"]))

    if not args.skip_premium:
        steps.append(
            _run(
                "premium_multilens_best_effort",
                [PY, "scripts/build_premium_btrack_multilens_report_v1.py", "--mode", "best-effort"],
                timeout=180,
            )
        )

    ok = all(s["exit_code"] == 0 for s in steps)
    abl = ROOT / "reports/kospi_four_lens_conditional_fusion_ablation_v1_latest.json"
    abl_summary = None
    if abl.is_file():
        try:
            abl_summary = json.loads(abl.read_text(encoding="utf-8-sig")).get("metrics")
        except json.JSONDecodeError:
            abl_summary = None

    out = ROOT / "reports/kospi_four_lens_graphrag_phase2_chain_v1_latest.json"
    doc = {
        "schema": "kospi_four_lens_graphrag_phase2_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "summary": {
            "ablation_metrics": abl_summary,
            "field_event_graph": "reports/field_kospi_event_graph_v1_latest.json",
            "fusion_md": "reports/kospi_four_lens_graphrag_fusion_v1_latest.md",
            "premium_md": "reports/premium_btrack_multilens_report_v1.md",
        },
        "reproduce": "py scripts/run_kospi_four_lens_graphrag_phase2_chain_v1.py",
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
