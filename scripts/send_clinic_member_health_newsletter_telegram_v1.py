#!/usr/bin/env python3
"""Send clinic member health newsletter draft to commander Telegram (relay · not to members)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_DRAFT = ART / "clinic_member_health_newsletter_draft_latest.json"
TELEGRAM_MAX = 4096


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ[key] = val


def _resolve_secret(name: str) -> str:
    direct = os.getenv(name, "").strip()
    if direct:
        return direct
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        got = get_security_agent().get_env_var(name)
        if got and str(got).strip():
            return str(got).strip()
    except Exception:
        pass
    return ""


def _send_telegram(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, f"http_{resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"http_{exc.code}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def build_text(draft: dict) -> str:
    text = str(draft.get("telegram_text") or "").strip()
    if not text:
        raise ValueError("draft missing telegram_text")
    return text[:TELEGRAM_MAX]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draft-json", type=Path, default=DEFAULT_DRAFT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    draft_path = args.draft_json if args.draft_json.is_absolute() else ROOT / args.draft_json
    if not draft_path.is_file():
        raise SystemExit(f"Missing draft: {draft_path}")
    draft = json.loads(draft_path.read_text(encoding="utf-8-sig"))
    text = build_text(draft)

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "text_preview": text[:600]}, ensure_ascii=False))
        return 0

    _load_dotenv()
    token = _resolve_secret("TELEGRAM_BOT_TOKEN")
    chat_id = _resolve_secret("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(json.dumps({"ok": True, "skipped": True, "reason": "telegram_not_configured"}, ensure_ascii=False))
        return 0

    ok, detail = _send_telegram(token, chat_id, text)
    print(json.dumps({"ok": ok, "detail": detail, "message": "commander_relay_only"}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
