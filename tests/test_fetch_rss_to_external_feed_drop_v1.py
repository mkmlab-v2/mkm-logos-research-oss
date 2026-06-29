from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / "scripts/fetch_rss_to_external_feed_drop_v1.py"
LOAD = ROOT / "scripts/load_external_feed_drop_with_fallback_v1.py"


def test_fetch_rss_dry_run_with_mock_feed(tmp_path: Path) -> None:
    sources = tmp_path / "sources.json"
    xml = b"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>Test headline</title><link>https://example.com/1</link>
    <description>Detail</description><pubDate>Sat, 10 May 2026 08:00:00 GMT</pubDate></item>
    </channel></rss>"""
    feed_file = tmp_path / "feed.xml"
    feed_file.write_bytes(xml)
    sources.write_text(
        json.dumps(
            {
                "feeds": [
                    {
                        "id": "mock",
                        "enabled": True,
                        "url": feed_file.as_uri(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    out = tmp_path / "drop.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(FETCH),
            "--sources-json",
            str(sources),
            "--output-json",
            str(out),
            "--max-per-feed",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "external_feed_drop_v1"
    assert len(doc["data"]) == 1
    assert doc["data"][0]["title"] == "Test headline"


def test_load_external_feed_drop_validates(tmp_path: Path) -> None:
    latest = tmp_path / "latest.json"
    latest.write_text(
        json.dumps(
            {
                "schema": "external_feed_drop_v1",
                "data": [{"id": "1", "title": "Hello", "url": "https://example.com/x"}],
            }
        ),
        encoding="utf-8",
    )
    validated = tmp_path / "validated.json"
    status = tmp_path / "status.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(LOAD),
            "--latest",
            str(latest),
            "--output",
            str(validated),
            "--status-output",
            str(status),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    st = json.loads(status.read_text(encoding="utf-8"))
    assert st["mode"] == "ok"
    assert st["items_count"] == 1
