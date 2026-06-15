"""[HYPO-3] MASK shadow registry sync — B-track staging pointers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_compression_mask_shadow_registry_sync_v1.py"
STAGING = ROOT / "docs/final/artifacts/compression_mask_shadow_registry_staging_v1.json"


def test_shadow_registry_sync_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert STAGING.is_file()
    doc = json.loads(STAGING.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_mask_shadow_registry_v1"
    assert doc["shadow_only"] is True
    assert doc["production_router_unchanged"] is True
    agg = doc["aggregate"]
    assert agg["all_entries_present"] is True
    assert len(doc.get("staging_env_pointers") or {}) >= 7


def test_shadow_registry_biz_manifest_row_count() -> None:
    from scripts.compression_mask_shadow_registry_v1_lib import build_registry

    reg = build_registry(workspace_root=ROOT)
    biz = next(e for e in reg["entries"] if e["entry_id"] == "biz_template_manifest")
    assert biz["row_count"] == 13
    assert biz["wire_family"] == "BIZ_MASK"
    assert biz["sha256"]


def test_shadow_registry_staging_env_keys() -> None:
    from scripts.compression_mask_shadow_registry_v1_lib import REGISTRY_ENTRIES, build_registry

    reg = build_registry(workspace_root=ROOT)
    keys = set(reg["staging_env_pointers"].keys())
    for meta in REGISTRY_ENTRIES:
        assert meta["staging_env_key"] in keys
