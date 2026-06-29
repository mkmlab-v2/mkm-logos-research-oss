#!/usr/bin/env python3
"""Request access to stabilityai/stable-audio-open-1.0 via HF ask-access endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "stabilityai/stable-audio-open-1.0"


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
    ap.add_argument("--model-id", default=os.environ.get("MKM_AUDIO_STABLE_AUDIO_MODEL", DEFAULT_MODEL))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = _load_token()
    if not token:
        print("[hf-ask-access] missing HF_TOKEN", file=sys.stderr)
        return 2

    import requests
    from huggingface_hub import HfApi
    from huggingface_hub.utils import build_hf_headers

    headers = build_hf_headers(token=token)
    who = HfApi(token=token).whoami()
    fine = ((who.get("auth") or {}).get("accessToken") or {}).get("fineGrained") or {}

    report: dict = {
        "schema": "request_lens_stable_audio_hf_access_v1",
        "model_id": args.model_id,
        "hf_account": {
            "name": who.get("name"),
            "token_display": ((who.get("auth") or {}).get("accessToken") or {}).get("displayName"),
        },
        "checks": {"hf_token_can_read_gated": fine.get("canReadGatedRepos")},
    }

    if fine.get("canReadGatedRepos") is False:
        report["blocker"] = (
            "HF_TOKEN fine-grained token lacks canReadGatedRepos — create new token at huggingface.co/settings/tokens"
        )
        out = ROOT / "reports/lens_stable_audio_hf_ask_access_v1_latest.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 1

    if report["checks"].get("hf_token_can_read_gated") is None:
        report["note"] = "classic_read_token_or_access_already_granted"
        out = ROOT / "reports/lens_stable_audio_hf_ask_access_v1_latest.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    body = {
        "Name": who.get("fullname") or who.get("name") or "moksorinw",
        "Email": who.get("email") or "",
        "Country": "KR",
        "Organization or Affiliation": "MKM",
        "Receive email updates and promotions on Stability AI products, services, and research?": "No",
        "What do you intend to use the model for?": "Research",
    }

    urls = [
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
        report[f"try_{url.split('/')[-2]}"] = {"status": resp.status_code, "body_preview": resp.text[:200]}
        if resp.status_code < 400:
            break

    url = last_url
    report["url"] = url
    report["http_status"] = resp.status_code
    try:
        report["response_json"] = resp.json()
    except Exception:
        report["response_text"] = resp.text[:500]

    out = ROOT / "reports/lens_stable_audio_hf_ask_access_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if resp.status_code >= 400:
        print(f"[hf-ask-access] FAIL {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        print(f"[hf-ask-access] WROTE {out}", file=sys.stderr)
        return 1

    print(f"[hf-ask-access] OK {resp.status_code} WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
