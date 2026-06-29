"""Build + schema smoke for showroom era insight lattice v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_showroom_era_insight_lattice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/showroom_era_insight_lattice_v1.schema.json"
GENESIS = ROOT / "docs/final/artifacts/showroom_era_insight_lattice_genesis_v1_latest.json"
MVP = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_era_insight_lattice_v1.json"
)


def test_build_lattice_exit_zero() -> None:
    proc = subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=False)
    assert proc.returncode == 0, "builder failed"
    assert GENESIS.is_file()
    assert MVP.is_file()


def test_genesis_lattice_structure() -> None:
    if not GENESIS.is_file():
        subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True)
    doc = json.loads(GENESIS.read_text(encoding="utf-8-sig"))
    assert doc["schema_version"] == "showroom_era_insight_lattice_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["research_only"] is True
    card_ids = [c["card_id"] for c in doc["cards"]]
    assert card_ids[:5] == ["field", "logos", "lemma", "parallel", "gap"]
    logos = next(c for c in doc["cards"] if c["card_id"] == "logos")
    evidence = logos.get("evidence_nodes") or []
    assert any(e.get("ref") == "Gen.1.1" for e in evidence)
    stub = next((e for e in evidence if e.get("ref") == "Gen.3.6"), None)
    assert stub is not None
    assert stub.get("corpus_gap") is True
    gap = next(c for c in doc["cards"] if c["card_id"] == "gap")
    chips = gap.get("gap_chips") or []
    assert len(chips) >= 2
    assert all(c.get("bridge_question_ko") for c in chips)
    blob = json.dumps(doc, ensure_ascii=False).lower()
    for bad in ("hallucination-free", "100% 차단", "완벽한", "甲木", "금화"):
        assert bad not in blob


def test_mvp_pack_has_genesis_key() -> None:
    if not MVP.is_file():
        subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True)
    pack = json.loads(MVP.read_text(encoding="utf-8-sig"))
    assert "era_genesis_order_and_fall" in (pack.get("lattices") or {})
    assert SCHEMA.is_file()
