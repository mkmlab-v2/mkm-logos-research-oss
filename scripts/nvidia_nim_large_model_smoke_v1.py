#!/usr/bin/env python3
"""NIM large-model smoke (70B-class). B-track only; writes JSON report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/nvidia_nim_large_model_smoke_v1_latest.json"
MODELS = [
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/nemotron-3-nano-30b-a3b",
    "meta/llama-3.3-70b-instruct",
]
PROMPT = (
    "Answer in Korean only. Three bullets [HYPO]: cloud 70B vs local 8B on "
    "16GB VRAM for research drafts. No trading advice."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", dest="models")
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    models = args.models or MODELS
    finished = datetime.now(timezone.utc).isoformat()
    doc = {
        "schema": "nvidia_nim_large_model_smoke_v1",
        "finished_at_utc": finished,
        "lane": "b_track_research_only",
        "runs": [],
    }
    ok_any = False
    for model in models:
        cp = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/nvidia_nim_chat_v1.py"),
                "chat",
                "--model",
                model,
                "--prompt",
                PROMPT,
                "--max-tokens",
                str(args.max_tokens),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        row = {"model": model, "exit_code": cp.returncode}
        report = ROOT / "reports/nvidia_nim_chat_v1_latest.json"
        if report.is_file():
            chat_doc = json.loads(report.read_text(encoding="utf-8"))
            chat = chat_doc.get("chat") or {}
            row["http_status"] = chat.get("http_status")
            row["ok"] = bool(chat.get("ok"))
            row["usage"] = chat.get("usage")
            row["preview"] = (chat.get("assistant_text") or "")[:400]
            if row["ok"]:
                ok_any = True
        else:
            row["ok"] = False
            row["stderr_tail"] = (cp.stderr or "")[-300:]
        doc["runs"].append(row)

    doc["ok"] = ok_any
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if ok_any:
        for r in doc["runs"]:
            if r.get("ok"):
                print(f"=== {r['model']} ===\n{r.get('preview', '')}\n")
        print(f"[ok] {args.out_json}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
