#!/usr/bin/env python3
"""Gate: Logos Studio lemma neighbor bridge v1.

Reproduce:
  py scripts/check_logos_studio_lemma_bridge_gate_v1.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SYNTH = ROOT / "scripts/synthesize_logos_studio_lemma_bridge_answer_v1.py"
INDEX = ROOT / "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_studio_lemma_bridge_gate_v1_latest.json"

CASES: list[dict[str, Any]] = [
    {
        "id": "psalm_23_neighbors",
        "query": "소망과 인내 시편",
        "verse_refs": ["Ps.23.1", "Ps.23.3", "Ps.23.4"],
        "min_neighbors": 1,
    },
    {
        "id": "daniel_2_neighbors",
        "query": "다니엘 2장",
        "verse_refs": ["Dan.2.10", "Dan.2.11"],
        "min_neighbors": 1,
    },
    {
        "id": "no_anchors_skip",
        "query": "빈 앵커",
        "verse_refs": [],
        "expect_ok": False,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    payload = {"query": case["query"], "path": {"verse_refs": case.get("verse_refs") or []}}
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json"],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {"ok": False, "error": "invalid_stdout", "stdout": proc.stdout[:300]}
    expect_ok = case.get("expect_ok", True)
    ok = proc.returncode == (0 if expect_ok else 1) and doc.get("ok") is expect_ok
    if expect_ok and case.get("min_neighbors"):
        ok = ok and int(doc.get("neighbor_count") or 0) >= int(case["min_neighbors"])
    if expect_ok:
        ok = ok and doc.get("synthesis_mode") == "deterministic_lemma_neighbor_bridge"
        ok = ok and "[HYPO]" in str(doc.get("answer_ko") or "")
    return {
        "id": case["id"],
        "ok": ok,
        "neighbor_count": doc.get("neighbor_count"),
        "synthesis_mode": doc.get("synthesis_mode"),
        "error": doc.get("error"),
    }


def main() -> int:
    if not INDEX.is_file():
        print(json.dumps({"ok": False, "error": f"missing_index: {INDEX}"}), file=sys.stderr)
        return 2
    results = [_run_case(c) for c in CASES]
    passed = sum(1 for r in results if r["ok"])
    doc = {
        "ok": passed == len(results),
        "passed": passed,
        "total": len(results),
        "generated_at_utc": _utc(),
        "cases": results,
        "reproduce": "py scripts/check_logos_studio_lemma_bridge_gate_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "passed": passed, "total": len(results), "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
