#!/usr/bin/env python3
"""B-track agent backend A/B smoke — same fixtures, Ollama vs optional cloud slot [HYPO].

Does not promote Track A, external validation SEND, or SOTA headline claims.
Cloud backend runs only when MKM_AGENT_BACKEND_CLOUD_SMOKE=1 (tier_15; paid API risk).
"""

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

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data/btrack/agent_backend_smoke_fixtures_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_agent_backend_smoke_v1_latest.json"
ENV_PATH = ROOT / ".env"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"
CLOUD_ENV = "MKM_AGENT_BACKEND_CLOUD_SMOKE"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _load_fixtures(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = doc.get("fixtures") or []
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"no fixtures in {path}")
    return rows


def _score(response: str, fx: dict[str, Any]) -> dict[str, Any]:
    text = (response or "").strip()
    lower = text.lower()
    need = [str(x) for x in (fx.get("pass_contains") or [])]
    min_chars = int(fx.get("min_chars") or 0)
    missing = [t for t in need if t.lower() not in lower and t not in text]
    char_ok = len(text) >= min_chars
    passed = char_ok and not missing
    return {
        "pass": passed,
        "char_ok": char_ok,
        "missing_contains": missing,
        "response_chars": len(text),
    }


def _ollama_generate(host: str, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    url = f"{host.rstrip('/')}/api/generate"
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        gen = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    text = str(gen.get("response") or "")
    return {
        "ok": bool(text.strip()),
        "response": text,
        "response_preview": text[:300],
        "latency_ms": elapsed_ms,
        "eval_duration_ns": gen.get("eval_duration"),
    }


def _cloud_generate(prompt: str, timeout: int) -> dict[str, Any]:
    """Optional cloud slot — OpenAI-compatible env; no hardcoded secrets."""
    base = (os.getenv("MKM_AGENT_BACKEND_CLOUD_BASE_URL") or "").strip().rstrip("/")
    model = (os.getenv("MKM_AGENT_BACKEND_CLOUD_MODEL") or "gpt-5.5").strip()
    api_key = (os.getenv("MKM_AGENT_BACKEND_CLOUD_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not base or not api_key:
        return {
            "ok": False,
            "skipped": True,
            "reason": "missing MKM_AGENT_BACKEND_CLOUD_BASE_URL or API key env",
        }
    url = f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        return {"ok": False, "error": f"HTTP {e.code}: {err_body}", "latency_ms": 0}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return {"ok": False, "error": str(e), "latency_ms": 0}
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    choices = doc.get("choices") or []
    text = ""
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        text = str(msg.get("content") or "")
    return {
        "ok": bool(text.strip()),
        "response": text,
        "response_preview": text[:300],
        "latency_ms": elapsed_ms,
        "model": model,
    }


def _run_backend(
    backend: str,
    fixtures: list[dict[str, Any]],
    *,
    dry_run: bool,
    ollama_host: str,
    ollama_model: str,
    timeout_sec: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for fx in fixtures:
        fx_id = str(fx.get("id") or "unknown")
        prompt = str(fx.get("prompt") or "")
        row: dict[str, Any] = {"fixture_id": fx_id, "category": fx.get("category"), "backend": backend}
        if dry_run:
            row.update({"skipped": True, "reason": "dry_run", "pass": None})
            rows.append(row)
            continue
        if backend == "cloud":
            if not _truthy(CLOUD_ENV):
                row.update(
                    {
                        "skipped": True,
                        "reason": f"{CLOUD_ENV} not set (tier_15)",
                        "pass": None,
                    }
                )
                rows.append(row)
                continue
            gen = _cloud_generate(prompt, timeout_sec)
        elif backend == "ollama":
            try:
                gen = _ollama_generate(ollama_host, ollama_model, prompt, timeout_sec)
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
                gen = {"ok": False, "error": str(e), "response": ""}
        else:
            raise ValueError(f"unknown backend: {backend}")

        if gen.get("skipped"):
            row.update(gen)
            rows.append(row)
            continue

        response = str(gen.get("response") or "")
        score = _score(response, fx)
        row.update(
            {
                "ok": bool(gen.get("ok")),
                "pass": score["pass"],
                "score": score,
                "latency_ms": gen.get("latency_ms"),
                "response_preview": gen.get("response_preview") or response[:300],
                "error": gen.get("error"),
            }
        )
        rows.append(row)

    attempted = [r for r in rows if not r.get("skipped")]
    passed = [r for r in attempted if r.get("pass")]
    return {
        "backend": backend,
        "dry_run": dry_run,
        "fixture_count": len(rows),
        "attempted": len(attempted),
        "passed": len(passed),
        "pass_rate": (len(passed) / len(attempted)) if attempted else None,
        "rows": rows,
    }


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--backends", default="ollama", help="comma list: ollama,cloud")
    ap.add_argument("--max-cases", type=int, default=0, help="0 = all fixtures")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ollama-host", default=os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST))
    ap.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL))
    ap.add_argument("--timeout-sec", type=int, default=120)
    args = ap.parse_args()

    fixtures = _load_fixtures(args.fixtures)
    if args.max_cases > 0:
        fixtures = fixtures[: args.max_cases]

    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    results = [
        _run_backend(
            b,
            fixtures,
            dry_run=args.dry_run,
            ollama_host=args.ollama_host.rstrip("/").replace("/v1", ""),
            ollama_model=args.ollama_model,
            timeout_sec=args.timeout_sec,
        )
        for b in backends
    ]

    repro = (
        f"py scripts/run_btrack_agent_backend_smoke_v1.py --backends {','.join(backends)}"
        + (" --dry-run" if args.dry_run else "")
        + (f" --max-cases {args.max_cases}" if args.max_cases else "")
    )

    doc = {
        "schema": "btrack_agent_backend_smoke_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
        "boundary_ack": (
            "Same-fixture backend smoke only; not Terminal-Bench/Codex/MiMo SOTA headline SSOT. "
            "Cloud slot tier_15; Ollama mainline not blocked."
        ),
        "fixtures_path": str(args.fixtures.relative_to(ROOT)).replace("\\", "/"),
        "backends": results,
        "cloud_enable_env": CLOUD_ENV,
        "reproducible_command": repro,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ollama_result = next((r for r in results if r["backend"] == "ollama"), None)
    exit_code = 0
    if args.dry_run:
        exit_code = 0
    elif ollama_result and ollama_result.get("attempted", 0) > 0:
        exit_code = 0 if ollama_result.get("passed", 0) > 0 else 1
    elif not args.dry_run and backends == ["cloud"]:
        exit_code = 0

    print(json.dumps({"ok": exit_code == 0, "out": str(args.out_json.relative_to(ROOT)), "exit_hint": exit_code}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
