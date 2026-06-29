#!/usr/bin/env python3
"""Phase-3: science_core backfill · shock ablation · myeongni corpus router."""
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
    ap.add_argument("--date-from", default="2026-06-20")
    ap.add_argument("--date-to", default="2026-06-23")
    ap.add_argument("--skip-science-merge", action="store_true")
    ap.add_argument("--skip-phase2", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_science_merge:
        steps.append(
            _run(
                "merge_science_core_kospi",
                [
                    PY,
                    "scripts/merge_btrack_science_core_per_date_kospi_v1.py",
                    "--date-from",
                    args.date_from,
                    "--date-to",
                    args.date_to,
                ],
            )
        )

    if not args.skip_phase2:
        steps.append(
            _run(
                "phase2_chain",
                [PY, "scripts/run_kospi_four_lens_graphrag_phase2_chain_v1.py", "--skip-premium"],
                timeout=420,
            )
        )
    else:
        steps.append(_run("rebuild_fusion", [PY, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py"]))

    steps.append(_run("build_myeongni_corpus_router", [PY, "scripts/build_myeongni_corpus_graphrag_router_v1.py"]))
    steps.append(_run("rebuild_field_event_graph", [PY, "scripts/build_field_kospi_event_graph_v1.py"]))
    steps.append(_run("shock_conditional_ablation", [PY, "scripts/run_kospi_four_lens_shock_conditional_ablation_v1.py"]))

    ok = all(s["exit_code"] == 0 for s in steps)

    shock_summary = None
    shock_path = ROOT / "reports/kospi_four_lens_shock_conditional_ablation_v1_latest.json"
    if shock_path.is_file():
        try:
            shock_doc = json.loads(shock_path.read_text(encoding="utf-8-sig"))
            shock_summary = shock_doc.get("comparison")
        except json.JSONDecodeError:
            shock_summary = None

    merge_summary = None
    merge_path = ROOT / "reports/merge_btrack_science_core_per_date_v1_latest.json"
    if merge_path.is_file():
        try:
            merge_summary = json.loads(merge_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            merge_summary = None

    out = ROOT / "reports/kospi_four_lens_graphrag_phase3_chain_v1_latest.json"
    doc = {
        "schema": "kospi_four_lens_graphrag_phase3_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "summary": {
            "science_core_merge": merge_summary,
            "shock_ablation_comparison": shock_summary,
            "myeongni_corpus_router": "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json",
            "field_event_graph": "reports/field_kospi_event_graph_v1_latest.json",
            "fusion_md": "reports/kospi_four_lens_graphrag_fusion_v1_latest.md",
        },
        "reproduce": "py scripts/run_kospi_four_lens_graphrag_phase3_chain_v1.py",
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
