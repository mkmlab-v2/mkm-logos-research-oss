"""KM classics vendor inventory v1 [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_km_classics_index_hypo_v1 import inventory_vendor_root  # noqa: E402

STUB = ROOT / "tests/fixtures/km_classics_vendor_stub_hypo_v1"


def test_inventory_stub_vendor() -> None:
    doc = inventory_vendor_root(STUB)
    assert doc["schema"] == "km_classics_index_hypo_v1"
    assert doc["file_count"] >= 2
    assert doc["personadiary_join"] is False
    ids = {e["source_id"] for e in doc["entries"]}
    assert len(ids) == len(doc["entries"])


def test_cli_writes_report(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "index.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_km_classics_index_hypo_v1.py"),
            "--vendor-root",
            str(STUB),
            "--out-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["file_count"] >= 2
