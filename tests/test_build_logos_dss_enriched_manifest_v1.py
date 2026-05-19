"""DSS enriched manifest builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_dss_enriched_manifest_v1.py"
DSS = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"


def test_dss_enriched_manifest_smoke(tmp_path: Path) -> None:
    inp = tmp_path / "dss.jsonl"
    inp.write_text(
        json.dumps(
            {
                "id": "dss_enriched_0001",
                "source": "dss",
                "source_doc": "docs/final/btrack_dss_1QS_pure_discipline.md",
                "text": "1Q Community Rule DSS evidence sample sentence for manifest test.",
                "ingested_at_utc": "2026-05-16T00:00:00Z",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "manifest.json"
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-jsonl", str(inp), "--output", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["row_count"] == 1


def test_dss_enriched_manifest_repo_path() -> None:
    if not DSS.is_file():
        return
    rc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
