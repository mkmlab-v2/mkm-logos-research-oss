"""DSS satellite lane builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_dss_satellite_lane_v1.py"


def test_dss_satellite_lane_offline(tmp_path: Path) -> None:
    inp = tmp_path / "dss.jsonl"
    inp.write_text(
        json.dumps(
            {
                "id": "dss_enriched_0001",
                "source": "dss",
                "source_doc": "docs/final/btrack_dss_1QS_pure_discipline.md",
                "text": "Community Rule 1QS DSS Qumran evidence for lane projection test sentence.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "lane.jsonl"
    man = tmp_path / "manifest.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-jsonl",
            str(inp),
            "--output-jsonl",
            str(out),
            "--manifest",
            str(man),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert row["schema"] == "logos_verse_4d_v1"
    assert row["lane"] == "dss"
    assert row["verse_id"].startswith("dss:")
    assert isinstance(row.get("vector_4d"), dict)
