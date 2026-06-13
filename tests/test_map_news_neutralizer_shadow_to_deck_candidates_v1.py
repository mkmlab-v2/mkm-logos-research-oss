from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP_SCRIPT = ROOT / "scripts" / "map_news_neutralizer_shadow_to_deck_candidates_v1.py"
NEUTRALIZER_SCRIPT = ROOT / "scripts" / "test_news_neutralizer_v1.py"
SCHEMA = ROOT / "docs/final/schemas/news_neutralizer_deck_candidates_v1.schema.json"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/mkmlife_news_observation_deck_v1.json"


def _run_map(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MAP_SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def _run_neutralizer(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(NEUTRALIZER_SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )


def test_map_script_exists() -> None:
    assert MAP_SCRIPT.is_file()


def test_fixture_chain_produces_candidates(tmp_path: Path) -> None:
    shadow = tmp_path / "shadow.json"
    out = tmp_path / "candidates.json"
    cp_n = _run_neutralizer("--dry-run", "--fixture", "--output-json", str(shadow), "--strict-lint")
    assert cp_n.returncode == 0, cp_n.stdout + cp_n.stderr
    cp = _run_map("--shadow-json", str(shadow), "--output-json", str(out), "--strict-lint")
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "news_neutralizer_deck_candidates_v1"
    assert doc["promotion_status"] == "pending_human"
    assert len(doc["candidate_cards"]) >= 1
    card = doc["candidate_cards"][0]
    assert card.get("hypothesis_tag") == "[HYPO]"
    assert isinstance(card.get("neutralizer_overlay"), dict)


def test_candidates_schema_validation(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    shadow = tmp_path / "shadow.json"
    out = tmp_path / "candidates.json"
    cp_n = _run_neutralizer("--dry-run", "--fixture", "--output-json", str(shadow))
    assert cp_n.returncode == 0, cp_n.stdout + cp_n.stderr
    cp = _run_map("--shadow-json", str(shadow), "--output-json", str(out))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def test_merge_blocked_without_human_ack(tmp_path: Path) -> None:
    shadow = tmp_path / "shadow.json"
    out = tmp_path / "candidates.json"
    deck = tmp_path / "deck.json"
    deck.write_text(
        json.dumps({"schema": "mkmlife_news_observation_deck_v1", "cards": []}),
        encoding="utf-8",
    )
    cp_n = _run_neutralizer("--dry-run", "--fixture", "--output-json", str(shadow))
    assert cp_n.returncode == 0
    cp = _run_map("--shadow-json", str(shadow), "--output-json", str(out))
    assert cp.returncode == 0
    cp_bad = _run_map(
        "--shadow-json",
        str(shadow),
        "--output-json",
        str(out),
        "--merge-into-deck-artifact",
        str(deck),
    )
    assert cp_bad.returncode == 1
    assert "human-ack" in (cp_bad.stderr or cp_bad.stdout).lower()


def test_public_deck_untouched_by_default(tmp_path: Path) -> None:
    if not MKMLIFE_PUBLIC.is_file():
        pytest.skip("public deck not present")
    before = MKMLIFE_PUBLIC.read_bytes()
    shadow = tmp_path / "shadow.json"
    out = tmp_path / "candidates.json"
    cp_n = _run_neutralizer("--dry-run", "--fixture", "--output-json", str(shadow))
    assert cp_n.returncode == 0
    cp = _run_map("--shadow-json", str(shadow), "--output-json", str(out))
    assert cp.returncode == 0
    assert MKMLIFE_PUBLIC.read_bytes() == before
