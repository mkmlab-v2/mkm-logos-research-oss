from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs/final/artifacts/fixtures/logos_verse_4d_v1.example.json"


def _minimal_verse(verse_id: str, text: str) -> dict:
    base = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    base["verse_id"] = verse_id
    base["text_span"]["original_script_text"] = text
    return base


def _tiny_codebook(tmp_path: Path) -> Path:
    p = tmp_path / "codebook.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 1,
                "entries": [
                    {
                        "atom_id": "hebrew::ברא",
                        "lang": "hebrew",
                        "normalized_form": "ברא",
                        "occurrences": 10,
                    },
                ],
                "inputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def test_atom_anchor_verse_pool_smoke(tmp_path: Path) -> None:
    verse_jsonl = tmp_path / "verses.jsonl"
    rows = [
        _minimal_verse("Gen.1.1", "ברא אלהים"),
        _minimal_verse("Gen.1.2", "ותהי הארץ"),
    ]
    with verse_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    codebook = _tiny_codebook(tmp_path)
    out = tmp_path / "pool.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/resolve_logos_atom_anchor_verse_pool_v1.py"),
            "--atom-id",
            "hebrew::ברא",
            "--verse-jsonl",
            str(verse_jsonl),
            "--codebook-json",
            str(codebook),
            "--out-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_atom_anchor_verse_pool_v1"
    ids = [v["verse_id"] for v in doc["pool"]["verse_pool"]]
    assert ids == ["Gen.1.1"]


def test_project_filter_atom_id(tmp_path: Path) -> None:
    if not EXAMPLE.is_file():
        pytest.skip("fixture missing")
    verse_jsonl = tmp_path / "verses.jsonl"
    verse_jsonl.write_text(
        json.dumps(_minimal_verse("Gen.1.1", "ברא"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    codebook = _tiny_codebook(tmp_path)
    out = tmp_path / "out.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/project_logos_verse_4d_to_lexicon_v1.py"),
            "--verse-jsonl",
            str(verse_jsonl),
            "--codebook-json",
            str(codebook),
            "--filter-atom-id",
            "hebrew::ברא",
            "--out-jsonl",
            str(out),
            "--skip-lexicon-4d",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
