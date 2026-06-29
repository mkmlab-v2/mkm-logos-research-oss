#!/usr/bin/env python3
"""Parallel retrieval ablations on bridge_v2 overlay: no-dedupe spike + seed-neighbor audit."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OVERLAY = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl"
FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
GOLD_FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_gold_reseed_v1.json"
OUT = ROOT / "reports/logos_4d_bridge_v2_retrieval_ablation_v1_latest.json"


def _run(cmd: list[str], step: str) -> dict:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return {"step": step, "exit_code": cp.returncode, "stdout": (cp.stdout or "").strip()[-1500:]}


def _organic(path: Path) -> str:
    if not path.is_file():
        return "missing"
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    hits = sum(1 for t in doc.get("topics") or [] if (t.get("seed_in_top_k") or []))
    return f"{hits}/{len(doc.get('topics') or [])}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=OVERLAY)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing overlay jsonl — run bridge v2 poc chain first"}))
        return 2

    spike_dedupe = ROOT / "reports/logos_topic_4d_resonance_spike_bridge_v2_no_dedupe_v1_latest.json"
    spike_gold = ROOT / "reports/logos_topic_4d_resonance_spike_bridge_v2_gold_reseed_v1_latest.json"
    neighbor = ROOT / "reports/logos_4d_seed_neighbor_retrieval_v1_latest.json"

    steps = [
        _run(
            [
                PY,
                str(ROOT / "scripts/build_logos_topic_4d_resonance_spike_v1.py"),
                "--jsonl",
                str(args.jsonl),
                "--topics-json",
                str(FIXTURE),
                "--no-dedupe-vectors",
                "--out-json",
                str(spike_dedupe),
            ],
            "spike_no_dedupe",
        ),
        _run(
            [
                PY,
                str(ROOT / "scripts/build_logos_topic_4d_resonance_spike_v1.py"),
                "--jsonl",
                str(args.jsonl),
                "--topics-json",
                str(GOLD_FIXTURE),
                "--out-json",
                str(spike_gold),
            ],
            "spike_gold_reseed",
        ),
        _run(
            [
                PY,
                str(ROOT / "scripts/audit_logos_4d_seed_neighbor_retrieval_v1.py"),
                "--jsonl",
                str(args.jsonl),
                "--topics-json",
                str(FIXTURE),
                "--out-json",
                str(neighbor),
            ],
            "seed_neighbor_audit",
        ),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)
    neighbor_doc = json.loads(neighbor.read_text(encoding="utf-8-sig")) if neighbor.is_file() else {}

    doc = {
        "schema": "logos_4d_bridge_v2_retrieval_ablation_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "final_action": "HOLD_EXPLORATION",
        "ok": ok,
        "steps": steps,
        "ablations": {
            "baseline_v2_dedupe": _organic(ROOT / "reports/logos_topic_4d_resonance_spike_bridge_v2_v1_latest.json"),
            "v2_no_dedupe": _organic(spike_dedupe),
            "v2_gold_reseed": _organic(spike_gold),
            "seed_neighbor_hits_top_k": (neighbor_doc.get("summary") or {}).get("seed_hits_top_k"),
            "seed_neighbor_topic_hits": (neighbor_doc.get("summary") or {}).get("organic_topic_spike_equivalent"),
        },
        "pointers": {
            "spike_no_dedupe": str(spike_dedupe.relative_to(ROOT)).replace("\\", "/"),
            "spike_gold_reseed": str(spike_gold.relative_to(ROOT)).replace("\\", "/"),
            "seed_neighbor": str(neighbor.relative_to(ROOT)).replace("\\", "/"),
        },
        "interpretation_guard": "Ablation explains retrieval vs discrimination — not Track A promotion.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "ablations": doc["ablations"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
