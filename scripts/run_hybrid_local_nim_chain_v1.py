#!/usr/bin/env python3
"""
Hybrid operator chain v1: local Ollama embed (optional) + NVIDIA NIM chat summary.

B-track / research_only — not Track A promotion. No K-Startup copy polish.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/hybrid_local_nim_chain_v1_latest.json"
DEFAULT_SOURCE = (
    "MKM hybrid lab: local RTX handles small models and embeddings; "
    "NVIDIA NIM handles large-model generation. Summarize tradeoffs in 3 Korean bullets."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-text", default=DEFAULT_SOURCE)
    ap.add_argument("--skip-embed", action="store_true", help="Skip nomic-embed-text call")
    ap.add_argument("--nim-prompt", default="", help="Override NIM prompt; default builds from embed")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    finished = datetime.now(timezone.utc).isoformat()
    doc: dict = {
        "schema": "hybrid_local_nim_chain_v1",
        "finished_at_utc": finished,
        "lane": "b_track_operator_hybrid",
        "research_only": True,
        "steps": {},
    }

    # Step 1 — local Ollama tags
    r1 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ollama_local_smoke_v1.py"),
            "--model",
            "llama3.1:8b",
            "--timeout-sec",
            "180",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    doc["steps"]["ollama_smoke"] = {"exit_code": r1.returncode}
    ollama_report = ROOT / "reports/ollama_local_smoke_v1_latest.json"
    if ollama_report.is_file():
        doc["steps"]["ollama_smoke"]["report"] = json.loads(
            ollama_report.read_text(encoding="utf-8")
        )

    embed_vec_len = None
    if not args.skip_embed:
        host = (os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/").replace(
            "/v1", ""
        )
        import urllib.request

        body = json.dumps({"model": "nomic-embed-text:latest", "prompt": args.source_text}).encode(
            "utf-8"
        )
        req = urllib.request.Request(
            f"{host}/api/embeddings",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                emb = json.loads(resp.read().decode("utf-8"))
            vec = emb.get("embedding") or []
            embed_vec_len = len(vec)
            doc["steps"]["local_embed"] = {
                "ok": embed_vec_len > 0,
                "model": "nomic-embed-text:latest",
                "dim": embed_vec_len,
            }
        except Exception as e:
            doc["steps"]["local_embed"] = {"ok": False, "error": str(e)}

    nim_prompt = args.nim_prompt.strip()
    if not nim_prompt:
        hint = f"[local_embed_dim={embed_vec_len}] " if embed_vec_len else ""
        nim_prompt = hint + args.source_text

    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/nvidia_nim_chat_v1.py"),
            "chat",
            "--model",
            "meta/llama-3.3-70b-instruct",
            "--prompt",
            nim_prompt,
            "--max-tokens",
            "512",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    doc["steps"]["nim_chat"] = {"exit_code": r2.returncode, "stdout_tail": (r2.stdout or "")[-800:]}
    nim_report = ROOT / "reports/nvidia_nim_chat_v1_latest.json"
    if nim_report.is_file():
        doc["steps"]["nim_chat"]["report"] = json.loads(nim_report.read_text(encoding="utf-8"))

    doc["ok"] = r1.returncode == 0 and r2.returncode == 0
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if doc["ok"] and nim_report.is_file():
        chat = doc["steps"]["nim_chat"]["report"].get("chat") or {}
        print(chat.get("assistant_text", r2.stdout))
        print(f"\n[ok] hybrid -> {args.out_json}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
