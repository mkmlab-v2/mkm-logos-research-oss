#!/usr/bin/env python3
"""Orchestrate KOSPI 4-lens GraphRAG fusion PoC chain [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/kospi_four_lens_graphrag_fusion_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    tail = ((cp.stdout or "") + (cp.stderr or "")).strip()[-800:]
    return {"step": name, "exit_code": cp.returncode, "tail": tail}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-lens-refresh", action="store_true")
    ap.add_argument("--skip-logos-crosswalk", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    phase1: list[tuple[str, list[str]]] = []
    if not args.skip_lens_refresh:
        phase1.extend(
            [
                ("run_lens_myeongni", [PY, "scripts/run_lens_myeongni.py"]),
                ("run_lens_sasang", [PY, "scripts/run_lens_sasang.py"]),
                ("run_lens_logos", [PY, "scripts/run_lens_logos.py"]),
            ]
        )
    if not args.skip_logos_crosswalk:
        phase1.append(
            (
                "build_kospi_logos_crosswalk",
                [PY, "scripts/build_kospi_june2026_logos_anchor_crosswalk_v1.py"],
            )
        )
    phase1.append(("build_cross_lens_rag_fusion", [PY, "scripts/build_cross_lens_rag_fusion_v1.py"]))

    with ThreadPoolExecutor(max_workers=min(4, max(1, len(phase1)))) as pool:
        futures = {pool.submit(_run, n, c): n for n, c in phase1}
        for fut in as_completed(futures):
            steps.append(fut.result())

    steps.sort(key=lambda s: [n for n, _ in phase1].index(s["step"]))

    steps.append(_run("build_four_lens_fusion", [PY, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py"]))

    fusion_path = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
    fusion_summary = None
    if fusion_path.is_file():
        try:
            fusion_summary = json.loads(fusion_path.read_text(encoding="utf-8-sig")).get("fusion_resolution")
        except json.JSONDecodeError:
            fusion_summary = None

    ok = all(s["exit_code"] == 0 for s in steps)
    doc = {
        "schema": "kospi_four_lens_graphrag_fusion_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "summary": {
            "final_action": (fusion_summary or {}).get("final_action"),
            "conflict_ids": (fusion_summary or {}).get("conflict_ids"),
            "fusion_json": "reports/kospi_four_lens_graphrag_fusion_v1_latest.json",
            "fusion_md": "reports/kospi_four_lens_graphrag_fusion_v1_latest.md",
        },
        "reproduce": "py scripts/run_kospi_four_lens_graphrag_fusion_chain_v1.py",
    }
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
