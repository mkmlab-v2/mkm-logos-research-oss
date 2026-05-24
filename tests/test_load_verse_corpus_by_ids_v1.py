from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/logos_verse_selective_corpus_min.jsonl"


def test_selective_load_roundtrip(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "outputs": {"verse_4d_jsonl": str(FIXTURE.relative_to(ROOT)).replace("\\", "/")},
            }
        ),
        encoding="utf-8",
    )
    ids_file = tmp_path / "ids.json"
    ids_file.write_text(
        json.dumps({"verse_node_ids": ["aramaic::Gen.1.1", "aramaic::Gen.1.2"]}),
        encoding="utf-8",
    )
    out_jsonl = tmp_path / "out.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/load_verse_corpus_by_ids_v1.py"),
            "--manifest-json",
            str(manifest),
            "--ids-file",
            str(ids_file),
            "--out-jsonl",
            str(out_jsonl),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    rows = [json.loads(ln) for ln in lines]
    assert {r["verse_id"] for r in rows} == {"aramaic::Gen.1.1", "aramaic::Gen.1.2"}
