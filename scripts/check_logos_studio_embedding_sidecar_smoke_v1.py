#!/usr/bin/env python3
"""Smoke: Logos Studio embedding sidecar health + encode latency."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_studio_embedding_sidecar_smoke_latest.json"
DEFAULT_PORT = 18765


def _http_json(method: str, url: str, payload: dict | None = None, timeout: float = 120.0) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--manage-process", action="store_true", help="Start sidecar if /health fails")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    proc: subprocess.Popen | None = None
    steps: list[dict] = []

    try:
        try:
            health = _http_json("GET", f"{base}/health", timeout=3.0)
            steps.append({"step": "health_existing", "ok": health.get("ok") is True})
        except (urllib.error.URLError, TimeoutError):
            if not args.manage_process:
                print("sidecar not reachable; pass --manage-process", file=sys.stderr)
                return 1
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "scripts/logos_studio_embedding_sidecar_v1.py"), "--port", str(args.port)],
                cwd=ROOT,
            )
            deadline = time.time() + 120.0
            health = {}
            while time.time() < deadline:
                try:
                    health = _http_json("GET", f"{base}/health", timeout=2.0)
                    if health.get("ok"):
                        break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.5)
            steps.append({"step": "health_after_spawn", "ok": health.get("ok") is True})
            if not health.get("ok"):
                return 1

        t0 = time.perf_counter()
        enc = _http_json("POST", f"{base}/encode", {"query": "네피림 전통"}, timeout=120.0)
        encode_total_ms = int((time.perf_counter() - t0) * 1000)
        ok = enc.get("ok") is True and isinstance(enc.get("vector"), list) and len(enc["vector"]) >= 8
        steps.append(
            {
                "step": "encode",
                "ok": ok,
                "encode_ms_reported": enc.get("encode_ms"),
                "encode_total_ms": encode_total_ms,
                "vector_dim": enc.get("vector_dim"),
            }
        )
        if not ok:
            return 1

        t1 = time.perf_counter()
        enc2 = _http_json("POST", f"{base}/encode", {"query": "감시자 천사"}, timeout=30.0)
        warm_ms = int((time.perf_counter() - t1) * 1000)
        warm_ok = enc2.get("ok") is True and warm_ms < encode_total_ms
        steps.append({"step": "encode_warm_second", "ok": warm_ok, "warm_total_ms": warm_ms})

        report = {
            "schema": "logos_studio_embedding_sidecar_smoke_v1",
            "ok": True,
            "base": base,
            "steps": steps,
            "reproduce": "py scripts/check_logos_studio_embedding_sidecar_smoke_v1.py --manage-process",
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.out}")
        return 0
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
