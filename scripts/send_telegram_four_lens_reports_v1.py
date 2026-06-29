#!/usr/bin/env python3
"""Send four Telegram messages: 명리 · 성경(Logos) · 사상 · 종합 (observation-only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ORDER = (
    ("myeongni", "1/4 명리"),
    ("logos", "2/4 성경"),
    ("sasang", "3/4 사상"),
    ("synthesis", "4/4 종합"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay-sec", type=float, default=1.2, help="Pause between messages")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    from build_telegram_four_lens_reports_v1 import build_four_lens_reports  # noqa: WPS433
    from send_telegram_minimal_ops_digest_v1 import (  # noqa: WPS433
        _load_dotenv,
        _resolve_secret,
        _send_telegram,
        _truthy,
    )

    _load_dotenv()
    if not args.force and not _truthy("MKM_TELEGRAM_FOUR_LENS_ENABLED", default=False):
        print("SKIP: MKM_TELEGRAM_FOUR_LENS_ENABLED not set (four_lens Telegram off)")
        return 0
    if not args.force and not _truthy("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", default=False):
        os.environ["MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED"] = "1"

    token = _resolve_secret("TELEGRAM_BOT_TOKEN")
    chat = _resolve_secret("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("SKIP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing", file=sys.stderr)
        return 0

    ws = args.workspace_root.resolve()
    try:
        from build_lens_maturity_self_score_v1 import write_lens_maturity_self_score  # noqa: WPS433

        p = write_lens_maturity_self_score(ws)
        print(f"REFRESH: {p}")
    except Exception as exc:
        print(f"WARN: lens maturity refresh skipped: {exc}", file=sys.stderr)
    reports = build_four_lens_reports(ws)
    results: list[dict] = []
    all_ok = True

    for key, label in ORDER:
        text = f"[{label}]\n{reports[key]}"
        print(f"\n=== {label} ===\n{text}\n")
        if args.dry_run:
            results.append({"lens": key, "label": label, "ok": True, "dry_run": True, "chars": len(text)})
            continue
        ok, msg = _send_telegram(token, chat, text)
        results.append({"lens": key, "label": label, "ok": ok, "result": msg, "chars": len(text)})
        if not ok:
            all_ok = False
        if key != "synthesis" and args.delay_sec > 0:
            time.sleep(args.delay_sec)

    out = {
        "schema": "telegram_four_lens_send_v1",
        "sent_at_utc": _utc_now(),
        "dry_run": args.dry_run,
        "all_ok": all_ok,
        "messages": results,
    }
    out_path = ws / "reports" / "telegram_four_lens_send_latest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0 if all_ok or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
