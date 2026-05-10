# -*- coding: utf-8 -*-
"""One-shot: mock OpenAI-compatible /v1/chat/completions -> 'B', run MC A/B bench + gate (local dev only)."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 11499


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if not self.path.rstrip("/").endswith("/v1/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"choices": [{"message": {"content": "B"}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def main() -> int:
    httpd = HTTPServer(("127.0.0.1", PORT), _Handler)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    time.sleep(0.25)
    base = f"http://127.0.0.1:{PORT}"
    bench = [
        sys.executable,
        str(ROOT / "scripts" / "run_truthfulqa_ab_benchmark_v1.py"),
        "--task",
        "mc",
        "--max-rows",
        "2",
        "--baseline-url",
        base,
        "--candidate-url",
        base,
        "--baseline-model",
        "stub-b",
        "--candidate-model",
        "stub-b",
        "--out-json",
        str(ROOT / "docs" / "final" / "artifacts" / "truthfulqa_ab_benchmark_latest.json"),
    ]
    r1 = subprocess.run(bench, cwd=str(ROOT))
    httpd.shutdown()
    if r1.returncode != 0:
        return r1.returncode
    gate = [
        sys.executable,
        str(ROOT / "scripts" / "check_truthfulqa_ab_gate_v1.py"),
        "--mc-json",
        str(ROOT / "docs" / "final" / "artifacts" / "truthfulqa_ab_benchmark_latest.json"),
        "--out-json",
        str(ROOT / "docs" / "final" / "artifacts" / "truthfulqa_ab_gate_latest.json"),
        "--mc-only",
    ]
    return subprocess.run(gate, cwd=str(ROOT)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
