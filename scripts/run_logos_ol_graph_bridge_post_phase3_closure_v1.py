#!/usr/bin/env python3
"""Post-Phase3 closure: evidence pack + deck MD + PDF export + alignment ([HYPO], HOLD)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_ol_graph_bridge_post_phase3_closure_v1_latest.json"
PDF_MANIFEST = ROOT / "reports/logos_ops_deck/logos_ol_bridge_deck_pdf_export_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pdf", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    ok = True

    step_cmds: list[tuple[str, list[str]]] = [
        ("evidence_pack", [sys.executable, str(ROOT / "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py")]),
        ("alignment", [sys.executable, str(ROOT / "scripts/build_logos_ol_graph_bridge_alignment_v1.py")]),
        ("deck_md", [sys.executable, str(ROOT / "scripts/build_logos_ol_bridge_deck_md_v1.py")]),
    ]
    if not args.skip_pdf:
        step_cmds.append(("deck_pdf", [sys.executable, str(ROOT / "scripts/export_logos_ol_bridge_deck_pdf_v1.py")]))

    for label, cmd in step_cmds:
        s = _run(cmd)
        steps.append({"step": label, **s})
        ok = ok and s["exit_code"] == 0

    pytest_exit: int | None = None
    if ok and not args.skip_pytest:
        s = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_ol_graph_bridge_post_phase3_closure_v1.py",
                "-q",
            ],
            timeout=300,
        )
        steps.append({"step": "pytest", **s})
        pytest_exit = s["exit_code"]
        ok = ok and pytest_exit == 0

    alignment_path = ROOT / "reports/logos_ol_graph_bridge_alignment_v1_latest.json"
    alignment_doc = (
        json.loads(alignment_path.read_text(encoding="utf-8")) if alignment_path.is_file() else {}
    )
    pdf_doc = json.loads(PDF_MANIFEST.read_text(encoding="utf-8")) if PDF_MANIFEST.is_file() else {}

    report = {
        "schema": "logos_ol_graph_bridge_post_phase3_closure_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ok": ok,
        "phase3_complete": alignment_doc.get("phase3_complete"),
        "deck_pdf_export_ok": pdf_doc.get("ok") if not args.skip_pdf else None,
        "human_signoff_required": True,
        "deck_pdf_manifest": str(PDF_MANIFEST.relative_to(ROOT)).replace("\\", "/")
        if PDF_MANIFEST.is_file()
        else None,
        "pytest_exit_code": pytest_exit,
        "steps": steps,
        "reproduce": "py scripts/run_logos_ol_graph_bridge_post_phase3_closure_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out_json),
                "deck_pdf_export_ok": report["deck_pdf_export_ok"],
                "human_signoff_required": True,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
