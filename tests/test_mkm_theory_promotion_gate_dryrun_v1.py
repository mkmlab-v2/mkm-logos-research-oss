from __future__ import annotations

import json
from pathlib import Path

from scripts import build_notebooklm_vault_sync_utf8_manifest_v1 as manifest_mod
from scripts import run_mkm_theory_formula_promotion_gate_dryrun_v1 as dryrun_mod


def test_utf8_manifest_lists_korean_paths(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "ws"
    for rel in manifest_mod.UTF8_SOURCE_FILES:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# stub\n", encoding="utf-8")

    out = root / "docs/final/artifacts/notebooklm_vault_sync_utf8_extra_paths_v1_latest.json"
    monkeypatch.setattr(manifest_mod, "ROOT", root)
    monkeypatch.setattr(manifest_mod, "OUT", out)
    assert manifest_mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert len(doc["source_files"]) == 3
    assert any("75" in p for p in doc["source_files"])


def test_promotion_gate_dryrun_ok(monkeypatch) -> None:
    assert dryrun_mod.main() == 0
    out = dryrun_mod.OUT
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["promotion_to_a_track_allowed"] is False
    names = {c.get("name") for c in doc.get("checks", [])}
    assert "compression_narrative_fact_lock" in names
