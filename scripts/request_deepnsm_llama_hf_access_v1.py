#!/usr/bin/env python3
"""Request meta-llama/Llama-3.2-1B gated access via HF API [HYPO]."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "meta-llama/Llama-3.2-1B"
DEFAULT_OUT = ROOT / "reports/deepnsm_llama_hf_ask_access_v1_latest.json"


def _load_token() -> str:
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("HF_TOKEN="):
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return os.environ.get("HF_TOKEN", "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-id", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    token = _load_token()
    if not token:
        print("[llama-ask-access] missing HF_TOKEN", file=sys.stderr)
        return 2

    import requests
    from huggingface_hub import HfApi
    from huggingface_hub.utils import build_hf_headers

    headers = build_hf_headers(token=token)
    who = HfApi(token=token).whoami()
    fine = ((who.get("auth") or {}).get("accessToken") or {}).get("fineGrained") or {}

    report: dict = {
        "schema": "request_deepnsm_llama_hf_access_v1",
        "model_id": args.model_id,
        "hf_account": {
            "name": who.get("name"),
            "email": who.get("email"),
            "token_display": ((who.get("auth") or {}).get("accessToken") or {}).get("displayName"),
        },
        "checks": {"hf_token_can_read_gated": fine.get("canReadGatedRepos")},
    }

    if fine.get("canReadGatedRepos") is False:
        report["blocker"] = (
            "HF_TOKEN fine-grained token lacks canReadGatedRepos — create new token at huggingface.co/settings/tokens"
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 1

    body = {
        "Name": who.get("fullname") or who.get("name") or "moksorinw",
        "Email": who.get("email") or "",
        "Country": "KR",
        "Organization or Affiliation": "MKM",
        "I agree to share my contact information with Meta": True,
    }

    urls = [
        f"https://huggingface.co/api/models/{args.model_id}/userAccessRequest/form",
        f"https://huggingface.co/api/models/{args.model_id}/ask-access",
        f"https://huggingface.co/models/{args.model_id}/ask-access",
    ]
    report["candidate_urls"] = urls

    if args.dry_run:
        report["status"] = "dry_run"
        print(json.dumps(report, ensure_ascii=False))
        return 0

    resp = None
    last_url = urls[0]
    for url in urls:
        last_url = url
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        report[f"try_{url.rstrip('/').split('/')[-1]}"] = {
            "url": url,
            "status": resp.status_code,
            "body_preview": resp.text[:300],
        }
        if resp.status_code < 400:
            break

    report["url"] = last_url
    report["http_status"] = resp.status_code
    try:
        report["response_json"] = resp.json()
    except Exception:
        report["response_text"] = resp.text[:500]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if resp.status_code >= 400:
        print(f"[llama-ask-access] FAIL {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        print(f"[llama-ask-access] WROTE {args.out}", file=sys.stderr)
        return 1

    print(f"[llama-ask-access] OK {resp.status_code} WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
