#!/usr/bin/env python3
"""[HYPO] Verify published Google Form URLs and fuse into registry + static hub (no submit)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "reports/gwangmyeong_baekje_b2b_google_form_urls_v1.json"
HUB = ROOT / "reports/demo/gwangmyeong_baekje_b2b_static_hub_v1.html"

FORM_KEYS = {
    "FORM-02": ("FORM-02_assignment", "#{과제_폼_URL}"),
    "FORM-03": ("FORM-03_qa", "#{QA_폼_URL}"),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _head_ok(url: str, timeout: float = 15.0) -> dict[str, object]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "MKM-form-register/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "url": url,
                "ok": 200 <= resp.status < 400,
                "status": resp.status,
                "elapsed_ms": elapsed_ms,
            }
    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"url": url, "ok": False, "status": e.code, "elapsed_ms": elapsed_ms, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"url": url, "ok": False, "status": None, "elapsed_ms": elapsed_ms, "error": str(e)}


def _validate_short(url: str) -> bool:
    return bool(re.match(r"^https://forms\.gle/[A-Za-z0-9_-]+$", url))


def _validate_responder(url: str) -> bool:
    return "docs.google.com/forms" in url and "/viewform" in url


def _patch_hub(placeholder: str, short_url: str) -> bool:
    if not HUB.is_file():
        return False
    raw = HUB.read_text(encoding="utf-8")
    needle = f'<span class="placeholder">{placeholder}</span>'
    if needle not in raw:
        return False
    link = f'<a href="{short_url}">{short_url}</a>'
    new_raw = raw.replace(needle, link, 1)
    if new_raw == raw:
        return False
    HUB.write_text(new_raw, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Register verified B2B form publish URLs")
    parser.add_argument("--form", required=True, choices=sorted(FORM_KEYS))
    parser.add_argument("--short-url", required=True)
    parser.add_argument("--responder-url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    short_url = args.short_url.strip()
    responder_url = args.responder_url.strip()
    if not _validate_short(short_url):
        print(json.dumps({"ok": False, "error": "invalid short_url (expect https://forms.gle/...)"}))
        return 1
    if not _validate_responder(responder_url):
        print(json.dumps({"ok": False, "error": "invalid responder_url (expect .../viewform)"}))
        return 1

    short_check = _head_ok(short_url)
    responder_check = _head_ok(responder_url)
    if not short_check.get("ok") or not responder_check.get("ok"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "HEAD verification failed — publish first, enable URL 단축, open responder in browser",
                    "short": short_check,
                    "responder": responder_check,
                },
                ensure_ascii=False,
            )
        )
        return 1

    if not REGISTRY.is_file():
        print(json.dumps({"ok": False, "error": f"missing registry: {REGISTRY}"}))
        return 1

    registry_key, hub_placeholder = FORM_KEYS[args.form]
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    forms = doc.setdefault("forms", {})
    entry = forms.setdefault(registry_key, {})
    entry["responder_url"] = responder_url
    entry["short_url"] = short_url
    entry["status"] = "published"
    entry["published_at_utc"] = _utc()
    entry.pop("unpublished_viewform_check", None)
    entry["draft_note"] = f"verified via register_gwangmyeong_baekje_b2b_form_publish_v1.py ({args.form})"
    doc["generated_at_utc"] = _utc()

    pending = doc.get("pending_human") or []
    done_markers = {
        "FORM-02": "FORM-02 게시",
        "FORM-03": "FORM-03 draft",
    }
    marker = done_markers.get(args.form)
    if marker:
        doc["pending_human"] = [p for p in pending if marker not in p]

    hub_patched = False
    if args.dry_run:
        hub_patched = hub_placeholder in HUB.read_text(encoding="utf-8")
    else:
        REGISTRY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hub_patched = _patch_hub(hub_placeholder, short_url)

    print(
        json.dumps(
            {
                "ok": True,
                "form": args.form,
                "registry_key": registry_key,
                "short_url": short_url,
                "responder_url": responder_url,
                "short_check": short_check,
                "responder_check": responder_check,
                "hub_patched": hub_patched,
                "dry_run": args.dry_run,
                "send_gate": doc.get("send_gate", "HOLD"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
