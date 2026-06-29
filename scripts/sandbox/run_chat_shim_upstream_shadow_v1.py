#!/usr/bin/env python3
"""[HYPO] Chat shim upstream shadow — 3 live requests, B-track research_only."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/chat_shim_upstream_shadow_v1_latest.json"
DEFAULT_PORT = 8011


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dotenv_into_environ() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        name, val = s.split("=", 1)
        name = name.strip()
        if name and name not in os.environ:
            os.environ[name] = val.strip().strip('"').strip("'")


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, *, timeout: float = 60) -> tuple[int, dict[str, Any] | str]:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _wait_health(port: int, *, seconds: float = 25) -> bool:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            code, doc = _http_json("GET", url, timeout=3)
            if code == 200 and isinstance(doc, dict) and doc.get("status") == "ok":
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    return False


def _sample_payloads() -> list[dict[str, Any]]:
    base_system = (
        "Task: shadow smoke only. "
        "Constraints: B-track research_only, no active report mutation, pytest smoke. "
        "Files: scripts/*.py. Verify with py -m pytest -q."
    )
    return [
        {
            "id": "shadow_01",
            "body": {
                "model": os.environ.get("MKM_CHAT_SHIM_UPSTREAM_MODEL", "gpt-4.1-mini"),
                "max_tokens": 32,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": base_system},
                    {"role": "user", "content": "Reply with exactly: OK_SHADOW_1"},
                ],
            },
        },
        {
            "id": "shadow_02",
            "body": {
                "model": os.environ.get("MKM_CHAT_SHIM_UPSTREAM_MODEL", "gpt-4.1-mini"),
                "max_tokens": 32,
                "temperature": 0,
                "messages": [
                    {"role": "user", "content": "One word: research_only"},
                ],
            },
        },
        {
            "id": "shadow_03",
            "body": {
                "model": os.environ.get("MKM_CHAT_SHIM_UPSTREAM_MODEL", "gpt-4.1-mini"),
                "max_tokens": 48,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "Constraints: pytest smoke, scripts/*.py"},
                    {"role": "user", "content": "Count constraints (number only)."},
                ],
            },
        },
    ]


def _is_transient_upstream_err(doc: Any) -> bool:
    if not isinstance(doc, dict):
        return False
    err = doc.get("error") or {}
    if not isinstance(err, dict):
        return False
    msg = str(err.get("message") or "").lower()
    return "503" in msg or "429" in msg or "unavailable" in msg or "too many requests" in msg


def _post_completion_with_retry(
    port: int,
    body: dict[str, Any],
    *,
    max_attempts: int = 4,
    base_sleep_s: float = 3.0,
) -> tuple[int, dict[str, Any] | str, int]:
    elapsed_ms = 0
    last: tuple[int, dict[str, Any] | str] = (0, {})
    for attempt in range(1, max_attempts + 1):
        t0 = time.perf_counter()
        code, doc = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/v1/chat/completions",
            body,
            timeout=120,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        last = (code, doc)
        if isinstance(doc, dict) and not doc.get("error"):
            return code, doc, elapsed_ms
        if isinstance(doc, dict) and _is_transient_upstream_err(doc) and attempt < max_attempts:
            time.sleep(base_sleep_s * attempt)
            continue
        return code, doc, elapsed_ms
    return last[0], last[1], elapsed_ms


def run_shadow(
    *,
    port: int,
    max_requests: int,
    dry_run: bool,
    reuse_running_shim: bool = False,
    request_delay_s: float = 2.0,
) -> dict[str, Any]:
    from scripts.sandbox.check_chat_shim_upstream_env_v1 import apply_upstream_env

    _load_dotenv_into_environ()
    cfg = apply_upstream_env()

    if dry_run:
        return {
            "schema": "chat_shim_upstream_shadow_v1",
            "dry_run": True,
            "upstream_configured": cfg.get("configured"),
            "max_requests": max_requests,
        }

    if not cfg.get("configured"):
        raise SystemExit("upstream_not_configured — set MKM_CHAT_SHIM_UPSTREAM_* in .env")

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(
        ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"
    )
    os.environ.pop("MKM_CHAT_SHIM_DRY_RUN", None)
    os.environ.setdefault("MKM_CHAT_SHIM_UPSTREAM_MODEL", str(cfg.get("model") or "gpt-4.1-mini"))

    proc: subprocess.Popen[Any] | None = None
    env = os.environ.copy()
    env["MKM_CHAT_SHIM_PORT"] = str(port)
    if reuse_running_shim and _wait_health(port, seconds=5):
        pass
    else:
        proc = subprocess.Popen(
            [sys.executable, "scripts/sandbox/launch_chat_shim_server_v1.py"],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    rows: list[dict[str, Any]] = []
    shadow_pass = False
    try:
        if not _wait_health(port):
            raise SystemExit("shim health timeout")

        health_code, health_doc = _http_json("GET", f"http://127.0.0.1:{port}/health")
        payloads = _sample_payloads()[: max(1, max_requests)]
        for idx, item in enumerate(payloads):
            if idx > 0 and request_delay_s > 0:
                time.sleep(request_delay_s)
            code, doc, elapsed_ms = _post_completion_with_retry(port, item["body"])
            ok = False
            audit = None
            usage = None
            assistant_preview = None
            err = None
            if isinstance(doc, dict):
                if doc.get("error"):
                    err = doc.get("error")
                else:
                    audit = (doc.get("mkm_shim_integrity") or {}).get("message_audit")
                    usage = doc.get("usage")
                    choices = doc.get("choices") or []
                    if choices and isinstance(choices[0], dict):
                        msg = choices[0].get("message") or {}
                        assistant_preview = str(msg.get("content") or "")[:120]
                    ok = bool(choices) and not doc.get("error")
            rows.append(
                {
                    "id": item["id"],
                    "http_status": code,
                    "elapsed_ms": elapsed_ms,
                    "pass": ok,
                    "usage": usage,
                    "structured_preserve_in_audit": any(
                        isinstance(a, dict) and a.get("structured_preserve")
                        for a in (audit or [])
                    ),
                    "assistant_preview": assistant_preview,
                    "error": err,
                }
            )
            if isinstance(err, dict) and "429" in str(err.get("message") or ""):
                break

        shadow_pass = len(rows) >= max_requests and all(r.get("pass") for r in rows)
        return {
            "schema": "chat_shim_upstream_shadow_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypothesis_tier": "B",
            "track_wall": "not_track_a_promotion",
            "upstream": {
                "configured": True,
                "base_url_hint": cfg.get("base_url_hint"),
                "model": os.environ.get("MKM_CHAT_SHIM_UPSTREAM_MODEL"),
                "key_source": cfg.get("key_source"),
                "dry_run": False,
            },
            "health": health_doc if isinstance(health_doc, dict) else {"status_code": health_code},
            "request_count": len(rows),
            "shadow_pass": shadow_pass,
            "requests": rows,
            "boundary_ack": "Shadow gates ready_for_upstream_live only; cursor override is signoff-gated separately.",
        }
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description="Chat shim upstream shadow (3 req).")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--max-requests", type=int, default=3)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument(
        "--reuse-running-shim",
        action="store_true",
        help="Skip spawn when :port /health is already ok (avoids port clash).",
    )
    ap.add_argument("--request-delay-s", type=float, default=2.0)
    args = ap.parse_args()

    doc = run_shadow(
        port=int(args.port),
        max_requests=max(1, int(args.max_requests)),
        dry_run=bool(args.dry_run),
        reuse_running_shim=bool(args.reuse_running_shim),
        request_delay_s=float(args.request_delay_s),
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    if not args.dry_run:
        print(f"shadow_pass={doc.get('shadow_pass')}")
    if args.strict and not doc.get("shadow_pass") and not args.dry_run:
        return 1
    if args.strict and args.dry_run and not doc.get("upstream_configured"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
