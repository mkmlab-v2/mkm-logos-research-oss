"""Offline smoke for Exa → news_observation PoC."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/fetch_exa_macro_news_observation_v1.py"
FIXTURE = {
    "results": [
        {
            "title": "Fed signals slower tightening as inflation cools",
            "url": "https://example.invalid/macro/1",
            "publishedDate": "2026-06-06T12:00:00Z",
            "text": "Risk assets rally while dollar softens on macro relief.",
        },
        {
            "title": "Oil spikes on Middle East supply concern",
            "url": "https://example.invalid/macro/2",
            "publishedDate": "2026-06-06T14:30:00Z",
            "text": "Energy equities lead risk-off bid in global markets.",
        },
    ]
}


def test_exa_macro_fetch_fixture_validate(tmp_path: Path) -> None:
    fixture_path = tmp_path / "exa_fixture.json"
    out_jsonl = tmp_path / "news.jsonl"
    fixture_path.write_text(json.dumps(FIXTURE), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fixture-json",
            str(fixture_path),
            "--output",
            str(out_jsonl),
            "--meta-json",
            str(tmp_path / "meta.json"),
            "--validate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["schema_version"] == "news_observation_v1"
    assert row["hypothesis_tag"] == "[HYPO]"
    assert row["source_id"] == "exa_macro_wire"
