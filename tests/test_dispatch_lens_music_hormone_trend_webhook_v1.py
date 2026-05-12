from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_hormone_trend_skips_without_webhook(tmp_path):
    trend = tmp_path / "trend.json"
    trend.write_text(
        json.dumps(
            {
                "schema": "lens_music_hormone_trend_v1",
                "generated_at_utc": "2026-05-11T00:00:00Z",
                "state": "WATCH",
                "rows_scanned": 7,
                "high_stress_rate": 0.4,
                "max_consecutive_high_stress": 4,
                "watch_thresholds": {"high_stress_rate": 0.25, "high_stress_consecutive": 3},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "dispatch.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dispatch_lens_music_hormone_trend_webhook_v1.py"),
            "--trend-json",
            str(trend),
            "--output-json",
            str(out),
            "--webhook-env",
            "MISSING_TEST_WEBHOOK",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_hormone_trend_webhook_dispatch_v1"
    assert doc["decision"]["dispatch_only_on_watch"] is True
    assert doc["dispatch"]["status"] == "skipped"
    assert doc["dispatch"]["reason"] == "webhook_not_configured"


def test_dispatch_hormone_trend_posts_when_watch_and_webhook_url(tmp_path):
    bodies: list[bytes] = []

    class _H(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            n = int(self.headers.get("Content-Length", "0") or 0)
            bodies.append(self.rfile.read(n))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), _H)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        port = int(server.server_address[1])
        url = f"http://127.0.0.1:{port}/hook"
        trend = tmp_path / "trend_watch.json"
        trend.write_text(
            json.dumps(
                {
                    "schema": "lens_music_hormone_trend_v1",
                    "generated_at_utc": "2026-05-11T00:00:00Z",
                    "state": "WATCH",
                    "rows_scanned": 7,
                    "high_stress_rate": 0.4,
                    "max_consecutive_high_stress": 4,
                    "watch_thresholds": {"high_stress_rate": 0.25, "high_stress_consecutive": 3},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        out = tmp_path / "dispatch_sent.json"
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/dispatch_lens_music_hormone_trend_webhook_v1.py"),
                "--trend-json",
                str(trend),
                "--output-json",
                str(out),
                "--webhook-url",
                url,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["dispatch"]["status"] == "sent"
        assert doc["dispatch"]["http_status"] == 200
        assert len(bodies) == 1
        posted = json.loads(bodies[0].decode("utf-8"))
        assert posted["source"] == "lens_music_hormone_trend_webhook_v1"
        assert posted["hormone_trend"]["state"] == "WATCH"
    finally:
        server.shutdown()
        th.join(timeout=5.0)
