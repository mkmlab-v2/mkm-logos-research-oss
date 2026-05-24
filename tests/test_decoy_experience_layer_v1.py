from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_decoy_zone_stubs_not_linked_to_corpus() -> None:
    for name in ("zone_tarot.json", "zone_mbti.json"):
        path = ROOT / "codebook/shards" / name
        assert path.is_file(), name
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("corpus_graph_wire_linked") is False


def test_decoy_bootstrap_exit() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/bootstrap_decoy_experience_zone_shards_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = ROOT / "docs/final/artifacts/decoy_experience_layer_readiness_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["d0_ok"] is True
    assert doc["no_trading_trigger"] is True


def test_registry_fifth_lane_decoy() -> None:
    from scripts.mkm_unified_asset_registry_v1 import assert_lane_isolation, resolve_lane  # noqa: WPS433

    assert_lane_isolation("decoy_experience_layer")
    res = resolve_lane("decoy_experience_layer")
    keys = {p.key for p in res.paths}
    assert "zone_tarot" in keys
    assert "zone_mbti" in keys
