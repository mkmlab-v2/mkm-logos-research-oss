"""Schema tests for v3 bilingual query set."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/bootstrap_logos_semantic_query_set_v3_bilingual_v1.py"
OUT = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json"
V3 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3.json"


def test_bootstrap_writes_v3_bilingual(tmp_path: Path) -> None:
    out = tmp_path / "v3_bilingual.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BOOTSTRAP),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_semantic_query_set_v3_bilingual_v1"
    assert len(doc["items"]) == 12
    for it in doc["items"]:
        assert it.get("query_en") and it.get("query_ko")


def test_v3_bilingual_aligns_with_v3_en_count() -> None:
    if not OUT.is_file():
        return
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    v3 = json.loads(V3.read_text(encoding="utf-8-sig"))
    assert len(doc["items"]) == len(v3["queries"])
