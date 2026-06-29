#!/usr/bin/env python3
"""Phase-4: shock fusion walk-forward · shock ablation refresh · premium attach."""
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
    ap.add_argument("--n-folds", type=int, default=4)
    args = ap.parse_args()

    steps: list[dict] = []

    steps.append(
        _run(
            "shock_fusion_walkforward",
            [
                PY,
                "scripts/run_kospi_four_lens_shock_fusion_walkforward_v1.py",
                "--n-folds",
                str(args.n_folds),
            ],
        )
    )
    steps.append(
        _run("shock_conditional_ablation", [PY, "scripts/run_kospi_four_lens_shock_conditional_ablation_v1.py"])
    )
    steps.append(
        _run(
            "conflict_band_coverage_wf",
            [
                PY,
                "scripts/run_kospi_four_lens_conflict_band_coverage_wf_v1.py",
                "--n-folds",
                str(args.n_folds),
            ],
        )
    )

    if not args.skip_premium:
        wf_md = ROOT / "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.md"
        premium_cmd = [
            PY,
            "scripts/build_premium_btrack_multilens_report_v1.py",
            "--mode",
            "best-effort",
        ]
        if wf_md.is_file():
            premium_cmd.extend(["--shock-fusion-wf-md", str(wf_md)])
        steps.append(_run("premium_multilens_best_effort", premium_cmd, timeout=180))

    ok = all(s["exit_code"] == 0 for s in steps)

    wf_summary = None
    wf_path = ROOT / "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.json"
    if wf_path.is_file():
        try:
            wf_doc = json.loads(wf_path.read_text(encoding="utf-8-sig"))
            wf_summary = {
                "comparison": wf_doc.get("comparison"),
                "promotion_ready": wf_doc.get("promotion_ready"),
                "holdout_pooled": wf_doc.get("holdout_pooled"),
                "n_folds": len(wf_doc.get("folds") or []),
            }
        except json.JSONDecodeError:
            wf_summary = None

    shock_summary = None
    shock_path = ROOT / "reports/kospi_four_lens_shock_conditional_ablation_v1_latest.json"
    if shock_path.is_file():
        try:
            shock_doc = json.loads(shock_path.read_text(encoding="utf-8-sig"))
            shock_summary = shock_doc.get("comparison")
        except json.JSONDecodeError:
            shock_summary = None

    band_summary = None
    band_path = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
    if band_path.is_file():
        try:
            band_doc = json.loads(band_path.read_text(encoding="utf-8-sig"))
            band_summary = {
                "comparison": band_doc.get("comparison"),
                "promotion_ready": band_doc.get("promotion_ready"),
                "holdout_pooled": band_doc.get("holdout_pooled"),
            }
        except json.JSONDecodeError:
            band_summary = None

    out = ROOT / "reports/kospi_four_lens_graphrag_phase4_chain_v1_latest.json"
    doc = {
        "schema": "kospi_four_lens_graphrag_phase4_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "ok": ok,
        "steps": steps,
        "summary": {
            "shock_fusion_walkforward": wf_summary,
            "shock_ablation_comparison": shock_summary,
            "band_coverage_wf": band_summary,
            "walkforward_json": "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.json",
            "band_coverage_json": "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json",
            "walkforward_md": "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.md",
            "fusion_md": "reports/kospi_four_lens_graphrag_fusion_v1_latest.md",
            "premium_md": "reports/premium_btrack_multilens_report_v1.md",
        },
        "reproduce": "py scripts/run_kospi_four_lens_graphrag_phase4_chain_v1.py",
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
