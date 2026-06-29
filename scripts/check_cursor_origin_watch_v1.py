#!/usr/bin/env python3
"""Lightweight watch: Cursor Origin / internal-git signals vs MKM internal-first policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "cursor_origin_watch_latest.json"
WATCH_URLS = (
    "https://www.cursor.com/changelog",
    "https://cursor.com/blog",
)
KEYWORDS = (
    "origin git",
    "origin",
    "internal git",
    "fallback",
    "self-hosted git",
    "enterprise git",
)
MKM_POLICY = {
    "internal_first_push": "scripts/push-internal.ps1",
    "github_exception": "scripts/Push-GitHub-Explicit.ps1 -Acknowledge",
    "action_on_signal": "compare_origin_git_with_internal_first_when_headline_appears",
}


def _fetch(url: str, timeout: float = 20.0) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MKM-CursorOriginWatch/1.0 (+https://a-codeai.com; ops-watch)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(500_000).decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(200_000).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body, str(exc)
    except Exception as exc:  # noqa: BLE001
        return None, "", str(exc)


def _scan(body: str) -> list[dict]:
    lowered = body.lower()
    hits: list[dict] = []
    for kw in KEYWORDS:
        if kw in lowered:
            hits.append({"keyword": kw, "count": lowered.count(kw)})
    # crude title-like snippets near "origin"
    for match in re.finditer(r"(?i).{0,80}origin.{0,80}", body):
        snippet = re.sub(r"\s+", " ", match.group(0)).strip()
        if len(snippet) > 20 and snippet not in {h.get("snippet") for h in hits if "snippet" in h}:
            hits.append({"snippet": snippet[:160]})
            if len([h for h in hits if "snippet" in h]) >= 5:
                break
    return hits


def run_watch(*, dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    report: dict = {
        "schema": "cursor_origin_watch_v1",
        "generated_at_utc": now.isoformat(),
        "mkm_policy": MKM_POLICY,
        "sources": [],
        "signal_detected": False,
        "operator_note_ko": "헤드라인에 Origin Git/내부 Git fallback이 보이면 push-internal.ps1·gitea와 30분 비교만 — 자동 전환 없음",
    }

    all_hits: list[dict] = []
    for url in WATCH_URLS:
        if dry_run:
            report["sources"].append({"url": url, "status": "dry_run_skipped"})
            continue
        status, body, err = _fetch(url)
        hits = _scan(body) if body else []
        all_hits.extend(hits)
        report["sources"].append(
            {
                "url": url,
                "http_status": status,
                "bytes": len(body),
                "error": err,
                "hits": hits[:8],
            }
        )

    report["signal_detected"] = any(
        h.get("keyword") in {"origin git", "internal git", "self-hosted git", "enterprise git"}
        for h in all_hits
        if "keyword" in h
    )
    report["all_hits"] = all_hits[:12]
    report["ok"] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Cursor Origin Git watch (observation only)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_watch(dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sig = report.get("signal_detected")
    print(f"CURSOR_ORIGIN_WATCH signal_detected={sig} ok={report.get('ok')}")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
