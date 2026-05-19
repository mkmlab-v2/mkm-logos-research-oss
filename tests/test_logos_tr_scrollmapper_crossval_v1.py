"""TR honza vs scrollmapper cross-validation (offline fixtures)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_tr_scrollmapper_crossval_v1.py"
FIXTURE_DIR = ROOT / "tests/fixtures/logos_tr_crossval"


@pytest.fixture()
def crossval_fixture(tmp_path: Path) -> dict[str, Path]:
    honza = tmp_path / "honza.jsonl"
    honza.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "verse_id": "Matt.1.1",
                        "greek_text": "Βίβλος γενέσεως Ἰησοῦ Χριστοῦ, υἱοῦ Δαβίδ, υἱοῦ Ἀβραάμ.",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "verse_id": "Jhn.3.16",
                        "greek_text": "Οὕτως γὰρ ἠγάπησεν ὁ θεὸς τὸν κόσμον.",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    scroll = tmp_path / "scrollmapper_TR.json"
    scroll.write_text(
        json.dumps(
            {
                "translation": "TR",
                "books": [
                    {
                        "name": "Matthew",
                        "chapters": [
                            {
                                "chapter": 1,
                                "verses": [
                                    {
                                        "verse": 1,
                                        "text": "βιβλος γενεσεως ιησου χριστου υιου δαβιδ υιου αβρααμ",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "name": "John",
                        "chapters": [
                            {
                                "chapter": 3,
                                "verses": [
                                    {
                                        "verse": 16,
                                        "text": "ουτως γαρ ηγαπησεν ο θεος τον κοσμον",
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "crossval.json"
    policy = tmp_path / "policy.jsonl"
    policy.write_text(
        json.dumps({"verse_id": "Matt.1.1"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"honza": honza, "scroll": scroll, "out": out, "policy": policy}


def test_scrollmapper_book_map() -> None:
    from scripts.logos_tr_scrollmapper_to_mt_verse_v1 import scrollmapper_verse_to_id

    assert scrollmapper_verse_to_id("I Corinthians", 13, 1) == "1Cor.13.1"
    assert scrollmapper_verse_to_id("Revelation of John", 1, 1) == "Rev.1.1"


def test_crossval_offline_fixture(crossval_fixture: dict[str, Path]) -> None:
    rc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--honza-jsonl",
            str(crossval_fixture["honza"]),
            "--cache-path",
            str(crossval_fixture["scroll"]),
            "--skip-download",
            "--policy-jsonl",
            str(crossval_fixture["policy"]),
            "--output",
            str(crossval_fixture["out"]),
            "--scope",
            "full_nt_overlap",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    doc = json.loads(crossval_fixture["out"].read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_tr_scrollmapper_crossval_v1"
    assert doc["counts"]["overlap_compared"] == 2
    assert doc["counts"]["normalized_exact_match"] == 2
    assert doc["gate"]["gap_15_of_15_normalized_match"] is True


@pytest.mark.skipif(not FIXTURE_DIR.is_dir(), reason="optional integration fixtures")
def test_normalize_helper_roundtrip() -> None:
    from scripts.logos_greek_text_normalize_v1 import normalize_greek_lexical

    a = normalize_greek_lexical("Βίβλος  γενέσεως.")
    b = normalize_greek_lexical("βιβλος γενεσεως")
    assert a == b
