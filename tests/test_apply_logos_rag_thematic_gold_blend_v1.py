"""Blend gold must not overwrite operational logos_semantic_query_gold_human_v1.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_logos_rag_thematic_gold_blend_v1.py"
SOURCE = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
BLEND = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_blend_v1.json"


def test_blend_writes_separate_file_preserves_source_mtime_content() -> None:
    if not SOURCE.is_file():
        return
    before = SOURCE.read_text(encoding="utf-8-sig")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--source-gold", str(SOURCE), "--out-json", str(BLEND)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    after = SOURCE.read_text(encoding="utf-8-sig")
    assert before == after
    assert BLEND.is_file()
    blend_doc = json.loads(BLEND.read_text(encoding="utf-8-sig"))
    assert blend_doc.get("status") == "commander_blend_eval_hypo_v1"
    assert "[HYPO]" in str(blend_doc.get("note") or "")
