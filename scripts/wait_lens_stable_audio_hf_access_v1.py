#!/usr/bin/env python3
"""Poll HF gated access until stable-audio-open is downloadable (or timeout)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "stabilityai/stable-audio-open-1.0"


def _load_token() -> str:
    tok = os.environ.get("HF_TOKEN", "").strip()
    if tok:
        return tok
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("HF_TOKEN="):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _probe(token: str, model_id: str) -> tuple[bool, str]:
    from huggingface_hub import HfApi, hf_hub_download

    try:
        who = HfApi(token=token).whoami()
        acct = who.get("name") or "?"
    except Exception as exc:
        return False, f"whoami:{type(exc).__name__}"

    try:
        hf_hub_download(model_id, "model_index.json", token=token)
        return True, acct
    except Exception as exc:
        return False, acct


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-id", default=os.environ.get("MKM_AUDIO_STABLE_AUDIO_MODEL", DEFAULT_MODEL))
    ap.add_argument("--interval-sec", type=float, default=15.0)
    ap.add_argument("--timeout-sec", type=float, default=180.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    token = _load_token()
    if not token:
        print("[hf-wait] missing HF_TOKEN in env or .env", file=sys.stderr)
        return 2

    url = f"https://huggingface.co/{args.model_id}"
    print(f"[hf-wait] Need Agree on model page (account must match HF_TOKEN): {url}", flush=True)

    deadline = time.monotonic() + args.timeout_sec
    while True:
        ok, info = _probe(token, args.model_id)
        if ok:
            print(f"[hf-wait] OK hf_model_access=true account={info}", flush=True)
            return 0
        print(f"[hf-wait] still gated (account={info}) — click Agree on {url}", flush=True)
        if args.once or time.monotonic() >= deadline:
            return 1
        time.sleep(max(1.0, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
