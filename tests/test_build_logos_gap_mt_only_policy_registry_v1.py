"""SA-S14: MT-only gap policy registry contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_gap_mt_only_policy_registry_v1.py"
OUT_JSONL = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
OUT_META = ROOT / "docs/final/artifacts/logos_gap_mt_only_policy_registry_v1_latest.json"


def test_build_mt_only_policy_registry_smoke() -> None:
    if not (ROOT / "reports/constitution/btrack_pilot/logos_verse_gap_ingest_queue_v1_latest.jsonl").is_file():
        return
    rc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert OUT_JSONL.is_file()
    assert OUT_META.is_file()
    meta = json.loads(OUT_META.read_text(encoding="utf-8"))
    assert meta["stub_count"] <= 148
    assert meta["decode_status_unified"] == "mt_canon_only_no_critical_text"
    rows = [json.loads(line) for line in OUT_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == meta["stub_count"]
    assert all(r["decode_status"] == "mt_canon_only_no_critical_text" for r in rows)
