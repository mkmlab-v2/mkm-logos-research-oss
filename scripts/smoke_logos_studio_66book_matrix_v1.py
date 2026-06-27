#!/usr/bin/env python3
"""Smoke: one API query per canon book anchor preset (66 OT+NT).

  py scripts/smoke_logos_studio_66book_matrix_v1.py
  py scripts/smoke_logos_studio_66book_matrix_v1.py --base https://logos.jema-ai.com
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.expand_logos_bible_full_corpus_batch_v1 import FULL_CANON_BOOK_ORDER  # noqa: E402

OUT = ROOT / "reports/logos_studio_66book_matrix_smoke_v1_latest.json"
DEFAULT_BASE = "https://logos.jema-ai.com"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _book_preset_id(book: str) -> str:
    return f"book_{book.lower()}_anchor"


def _fetch_json(url: str, *, method: str = "GET", body: dict[str, Any] | None = None, timeout: int = 45) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "MKM-LogosStudioSmoke/1.0 (+research_only)",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=DEFAULT_BASE, help="Studio origin (no trailing slash)")
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--books", default="", help="Comma-separated book codes subset (default: all 66)")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    presets_doc = _fetch_json(f"{base}/api/logos-research/presets", timeout=args.timeout)
    if presets_doc.get("ok") is not True:
        print(json.dumps({"ok": False, "error": "presets_failed"}, ensure_ascii=False))
        return 1
    preset_ids = {str(p.get("id")) for p in presets_doc.get("presets") or [] if p.get("id")}

    books = (
        [b.strip() for b in args.books.split(",") if b.strip()]
        if args.books.strip()
        else list(FULL_CANON_BOOK_ORDER)
    )

    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for book in books:
        pid = _book_preset_id(book)
        if pid not in preset_ids:
            failures.append(f"missing_preset:{book}")
            results.append({"book": book, "preset_id": pid, "ok": False, "reason": "preset_missing"})
            continue
        try:
            qdoc = _fetch_json(
                f"{base}/api/logos-research/query",
                method="POST",
                body={"preset_id": pid, "embed_demo": True},
                timeout=args.timeout,
            )
        except urllib.error.HTTPError as e:
            failures.append(f"http_{book}:{e.code}")
            results.append({"book": book, "preset_id": pid, "ok": False, "reason": f"http_{e.code}"})
            continue
        except Exception as e:
            failures.append(f"error_{book}:{type(e).__name__}")
            results.append({"book": book, "preset_id": pid, "ok": False, "reason": str(e)[:120]})
            continue

        ok = qdoc.get("ok") is True
        result = qdoc.get("result") or {}
        verse_refs = (result.get("path") or {}).get("verse_refs") or []
        answer_len = len(str(result.get("answer") or ""))
        if not ok:
            failures.append(f"query_fail:{book}")
        elif not verse_refs and answer_len < 40:
            failures.append(f"empty_result:{book}")
            ok = False

        results.append(
            {
                "book": book,
                "preset_id": pid,
                "ok": ok,
                "verse_refs": len(verse_refs),
                "answer_len": answer_len,
                "query_mode": result.get("query_mode"),
            }
        )

    passed = sum(1 for r in results if r.get("ok"))
    doc = {
        "schema": "logos_studio_66book_matrix_smoke_v1",
        "generated_at_utc": _utc(),
        "base": base,
        "research_only": True,
        "send_gate": "HOLD",
        "ok": len(failures) == 0 and passed == len(books),
        "books_requested": len(books),
        "books_passed": passed,
        "failures": failures[:32],
        "results": results,
        "reproduce": f"py scripts/smoke_logos_studio_66book_matrix_v1.py --base {base}",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "books_passed": passed, "books_requested": len(books), "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
