#!/usr/bin/env python3
"""[HYPO] Blend thematic gold eval — writes separate gold file; does not touch operational SSOT."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_SOURCE = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_BLEND_GOLD = ART / "logos_semantic_query_gold_human_blend_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_thematic_blend_eval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-gold", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--blend-gold", type=Path, default=DEFAULT_BLEND_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    blend_cmd = [
        py,
        str(ROOT / "scripts/apply_logos_rag_thematic_gold_blend_v1.py"),
        "--source-gold",
        str(args.source_gold),
        "--out-json",
        str(args.blend_gold),
    ]
    proc = subprocess.run(blend_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    eval_cmd = [
        py,
        str(ROOT / "scripts/run_logos_rag_dual_gold_eval_v1.py"),
        "--gold-json",
        str(args.blend_gold),
        "--output-json",
        str(args.output_json),
    ]
    proc2 = subprocess.run(eval_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc2.returncode != 0:
        print(proc2.stderr or proc2.stdout, file=sys.stderr)
        return proc2.returncode

    summary: dict[str, Any] = {}
    if args.output_json.is_file():
        summary = json.loads(args.output_json.read_text(encoding="utf-8-sig")).get("summary") or {}

    doc = {
        "schema": "comp_logos_rag_thematic_blend_eval_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "Not operational gold; do not cite as MS/RAG headline KPI.",
        "source_gold": str(args.source_gold),
        "blend_gold": str(args.blend_gold),
        "dual_eval_json": str(args.output_json),
        "summary": summary,
    }
    sidecar = PILOT / "comp_logos_rag_thematic_blend_eval_v1_sidecar_latest.json"
    sidecar.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "summary": summary, "out": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
