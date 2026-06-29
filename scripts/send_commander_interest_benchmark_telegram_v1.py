#!/usr/bin/env python3
"""Send compact commander interest benchmark digest to Telegram (skip if unset)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_WEEKLY = ART / "commander_interest_benchmark_weekly_latest.json"
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


def build_text(weekly: dict[str, Any], *, top_k: int = 3) -> str:
    lines = [
        "📊 관심분야 벤치마크 (주간)",
        f"window {weekly.get('window_days')}d · signals {weekly.get('signals_in_window')}",
        "— 참고용 · human publish only —",
        "",
    ]
    for idx, item in enumerate((weekly.get("top_items") or [])[:top_k], start=1):
        title = str(item.get("title") or "—")[:120]
        lines.append(
            f"{idx}) [{item.get('topic_label_ko')}] {title}\n"
            f"   score {item.get('engagement_score')} · {item.get('platform')}"
        )
        url = str(item.get("url") or "").strip()
        if url:
            lines.append(f"   {url}")
    lines.append("")
    lines.append("카드/팟캐스트: commander_ai_native_*_latest.md")
    text = "\n".join(lines)
    return text[:TELEGRAM_MAX]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    weekly_path = args.weekly_json if args.weekly_json.is_absolute() else ROOT / args.weekly_json
    if not weekly_path.is_file():
        raise SystemExit(f"Missing weekly report: {weekly_path}")
    weekly = json.loads(weekly_path.read_text(encoding="utf-8-sig"))
    text = build_text(weekly, top_k=args.top_k)

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "text_preview": text[:500]}, ensure_ascii=False))
        return 0

    _load_dotenv()
    token = _resolve_secret("TELEGRAM_BOT_TOKEN")
    chat_id = _resolve_secret("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(json.dumps({"ok": True, "skipped": True, "reason": "telegram_not_configured"}, ensure_ascii=False))
        return 0

    ok, detail = _send_telegram(token, chat_id, text)
    print(json.dumps({"ok": ok, "detail": detail}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
