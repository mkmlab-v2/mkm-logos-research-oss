"""TR variant vector builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_tr_variant_vectors_v1.py"
FIXTURE = ROOT / "tests/fixtures/tr_greek_gap_sample_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/logos_tr_variant_vectors_fixture_v1_latest.jsonl"


@pytest.fixture(scope="module")
def fixture_jsonl() -> Path:
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        json.dumps(
            {
                "verse_id": "Matt.18.11",
                "greek_text": "Ἦλθεν γὰρ ὁ υἱὸς τοῦ ἀνθρώπου σῶσαι τὸ ἀπολωλός.",
                "source_id": "TR_SCRIVENER_1894_HONZA",
                "license_tag": "honza_free_use_v1",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return FIXTURE


def test_build_tr_variant_vectors_from_fixture(fixture_jsonl: Path) -> None:
    rc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-jsonl",
            str(fixture_jsonl),
            "--output-jsonl",
            str(OUT),
            "--all-input-rows",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    row = json.loads(OUT.read_text(encoding="utf-8").strip())
    assert row["verse_id"] == "Matt.18.11"
    assert set(row["vector_4d"]) == {"S", "L", "K", "M"}
