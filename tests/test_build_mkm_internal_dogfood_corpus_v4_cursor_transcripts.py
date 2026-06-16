from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_mkm_internal_dogfood_corpus_v4_cursor_transcripts.py"
OUT = ROOT / "data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl"
META = ROOT / "reports/mkm_internal_dogfood_corpus_build_v4_cursor_transcripts_latest.json"
TRANSCRIPT = Path(
    r"C:\Users\PRO\.cursor\projects\c-workspace\agent-transcripts\33032686-3e11-4bd6-826a-b18b109b1150\33032686-3e11-4bd6-826a-b18b109b1150.jsonl"
)


def test_build_cursor_transcript_dogfood_v4_exit0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--transcript-jsonl",
            str(TRANSCRIPT),
            "--rows",
            "24",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    assert META.is_file()

    lines = [ln for ln in OUT.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 20
    assert len(lines) <= 24
    rows = [json.loads(ln) for ln in lines]
    assert all(r["domain_tag"] == "cursor_transcript" for r in rows)
    assert all(r["dogfood"] is True for r in rows)
    assert all(r["pii_scrubbed"] is True for r in rows)

    joined = "\n".join(r["text"] for r in rows)
    assert "C:\\workspace" not in joined
    assert "C:/workspace" not in joined
    assert "http://" not in joined
    assert "https://" not in joined

    meta = json.loads(META.read_text(encoding="utf-8-sig"))
    assert meta["schema"] == "mkm_internal_dogfood_corpus_build_v4_cursor_transcripts"
    assert meta["row_count"] == len(rows)
    assert meta["tenant_recommendation"] == "mkm-internal-dogfood-v4-cursor"

