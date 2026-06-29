"""Offline smoke for Exa weekly news backfill."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/backfill_exa_macro_news_observation_v1.py"
FIXTURE = ROOT / "tests/fixtures/exa_macro_news_fetch_fixture_v1.json"


def test_iter_date_windows_weekly() -> None:
    from scripts.backfill_exa_macro_news_observation_v1 import iter_date_windows

    wins = list(iter_date_windows("2026-01-01", "2026-01-20", step_days=7))
    assert wins[0] == ("2026-01-01", "2026-01-07")
    assert wins[-1][0] == "2026-01-15"
    assert wins[-1][1] == "2026-01-20"


def test_backfill_fixture_dedupe(tmp_path: Path) -> None:
    out = tmp_path / "news.jsonl"
    out.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "published_utc": "2026-01-02T00:00:00Z",
                "as_of_utc": "2026-01-02T00:00:00Z",
                "canonical_text": "existing row",
                "text_sha256": "deadbeef",
                "hypothesis_tag": "[HYPO]",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--date-from",
            "2026-01-01",
            "--date-to",
            "2026-01-07",
            "--max-windows",
            "1",
            "--fixture-json",
            str(FIXTURE),
            "--output",
            str(out),
            "--meta-json",
            str(tmp_path / "meta.json"),
            "--artifact-meta",
            str(tmp_path / "art.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["rows_appended"] >= 1
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 2
