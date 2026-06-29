from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "check_mkmlife_portal_commercialization_gate_v1.py"
DECK = ROOT / "projects/mkm/mkm-life/public/data/mkmlife_news_observation_deck_v1.json"


def test_portal_commercialization_gate_cli_passes_on_repo_deck(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(GATE), "--deck-json", str(DECK), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["overall_ok"] is True
    assert doc["checks"]["deck_json"]["card_count"] >= 1
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    for card in deck.get("cards") or []:
        blob = json.dumps(card, ensure_ascii=False)
        assert "속보" not in blob


def test_portal_commercialization_gate_fails_on_forbidden_deck(tmp_path: Path) -> None:
    bad = tmp_path / "bad_deck.json"
    base = json.loads(DECK.read_text(encoding="utf-8"))
    base["cards"][0]["headline_display_ko"] = "실시간 속보 테스트"
    bad.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(GATE), "--deck-json", str(bad), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["overall_ok"] is False
    assert doc["checks"]["deck_json"]["card_forbidden_hits"]
