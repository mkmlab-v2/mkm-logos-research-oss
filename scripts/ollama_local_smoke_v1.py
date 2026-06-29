#!/usr/bin/env python3
"""Local Ollama smoke — tags + one non-stream generate. No secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_OUT = ROOT / "reports/ollama_local_smoke_v1_latest.json"
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_PROMPT = "Reply in one short Korean sentence: local Ollama inference OK."


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _host() -> str:
    return (os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/").replace("/v1", "")


def _model() -> str:
    return os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL


def _get_tags(host: str, timeout: int) -> dict:
    url = f"{host}/api/tags"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _generate(
    host: str, model: str, prompt: str, timeout: int, system: str | None = None
) -> dict:
    url = f"{host}/api/generate"
    body: dict = {"model": model, "prompt": prompt, "stream": False}
    if system:
        body["system"] = system
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=_model())
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--system", default="", help="Ollama system prompt (optional)")
    ap.add_argument(
        "--system-file",
        type=Path,
        default=None,
        help="Read system prompt from file; {{DATE}} -> local Asia/Seoul date",
    )
    ap.add_argument("--timeout-sec", type=int, default=300)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    system = (args.system or "").strip()
    if args.system_file:
        from zoneinfo import ZoneInfo

        tpl = args.system_file.read_text(encoding="utf-8")
        local_date = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
        system = tpl.replace("{{DATE}}", local_date).strip()
    host = _host()
    doc: dict = {
        "schema": "ollama_local_smoke_v1",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "model": args.model,
        "lane": "local_infra_operator",
        "system_injected": bool(system),
    }
    if system:
        doc["system_preview"] = system[:400]
    try:
        tags = _get_tags(host, timeout=10)
        names = [m.get("name") for m in (tags.get("models") or []) if m.get("name")]
        doc["tags_ok"] = True
        doc["model_count"] = len(names)
        doc["model_installed"] = args.model in names or any(
            args.model.split(":")[0] in n for n in names
        )
        if not doc["model_installed"]:
            doc["ok"] = False
            doc["error"] = f"model not in tags: {args.model}"
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
            return 2
        gen = _generate(host, args.model, args.prompt, args.timeout_sec, system or None)
        doc["generate_ok"] = True
        doc["response_preview"] = (gen.get("response") or "")[:500]
        doc["eval_duration_ns"] = gen.get("eval_duration")
        doc["load_duration_ns"] = gen.get("load_duration")
        doc["ok"] = bool(doc.get("response_preview"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        doc["ok"] = False
        doc["error"] = str(e)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if doc.get("ok"):
        print(doc.get("response_preview", ""))
        print(f"\n[ok] {args.out_json}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
