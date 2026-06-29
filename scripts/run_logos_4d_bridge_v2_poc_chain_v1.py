#!/usr/bin/env python3
"""One-shot B-track PoC: bridge_v2 overlay → dedupe → organic spike → compare."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

OVERLAY = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl"
DEDUPE = ROOT / "reports/logos_verse_4d_dedupe_audit_bridge_v2_v1_latest.json"
SPIKE = ROOT / "reports/logos_topic_4d_resonance_spike_bridge_v2_v1_latest.json"
COMPARE = ROOT / "reports/logos_4d_bridge_v2_poc_compare_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"


def _run(cmd: list[str], *, step: str) -> dict:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return {
        "step": step,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "stdout": (cp.stdout or "").strip()[-2000:],
        "stderr": (cp.stderr or "").strip()[-1000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl")
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/logos_4d_bridge_v2_poc_chain_v1_latest.json")
    args = ap.parse_args()

    steps: list[dict] = []
    overlay_cmd = [
        PY,
        str(ROOT / "scripts/build_logos_verse_4d_bridge_v2_overlay_v1.py"),
        "--input-jsonl",
        str(args.input_jsonl),
        "--out-jsonl",
        str(OVERLAY),
    ]
    if args.max_rows:
        overlay_cmd.extend(["--max-rows", str(args.max_rows)])
    steps.append(_run(overlay_cmd, step="overlay"))
    if steps[-1]["exit_code"] != 0:
        return _fail(args.out_json, steps)

    steps.append(
        _run(
            [
                PY,
                str(ROOT / "scripts/audit_logos_verse_4d_dedupe_v1.py"),
                "--jsonl",
                str(OVERLAY),
                "--out-json",
                str(DEDUPE),
                "--topics-json",
                str(FIXTURE),
            ],
            step="dedupe",
        )
    )
    if steps[-1]["exit_code"] != 0:
        return _fail(args.out_json, steps)

    steps.append(
        _run(
            [
                PY,
                str(ROOT / "scripts/build_logos_topic_4d_resonance_spike_v1.py"),
                "--jsonl",
                str(OVERLAY),
                "--topics-json",
                str(FIXTURE),
                "--out-json",
                str(SPIKE),
            ],
            step="spike",
        )
    )
    if steps[-1]["exit_code"] != 0:
        return _fail(args.out_json, steps)

    steps.append(
        _run(
            [
                PY,
                str(ROOT / "scripts/compare_logos_4d_bridge_v2_poc_v1.py"),
                "--v2-dedupe",
                str(DEDUPE),
                "--v2-spike",
                str(SPIKE),
                "--out-json",
                str(COMPARE),
            ],
            step="compare",
        )
    )
    if steps[-1]["exit_code"] != 0:
        return _fail(args.out_json, steps)

    compare = json.loads(COMPARE.read_text(encoding="utf-8-sig")) if COMPARE.is_file() else {}
    doc = {
        "schema": "logos_4d_bridge_v2_poc_chain_v1",
        "ok": True,
        "research_only": True,
        "steps": steps,
        "compare_pointer": str(COMPARE.relative_to(ROOT)).replace("\\", "/"),
        "research_poc_pass": compare.get("research_poc_pass"),
        "final_action": compare.get("final_action", "HOLD_EXPLORATION"),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "research_poc_pass": doc["research_poc_pass"], "out": str(args.out_json)}))
    return 0


def _fail(out_path: Path, steps: list[dict]) -> int:
    doc = {"schema": "logos_4d_bridge_v2_poc_chain_v1", "ok": False, "steps": steps}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": False, "failed_step": steps[-1]["step"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
