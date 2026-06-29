#!/usr/bin/env python3
"""Bind known on-disk cheonyucho partial pastes into physical proxy tier ([HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/research/raw"
BIND = ROOT / "scripts/bind_cheonyucho_physical_anchor_v1.py"
P344_ANCHOR = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_p344_v1.json"

KNOWN: list[dict[str, str]] = [
    {
        "paste_file": "data/corpus/ijeoma/originals/cheonyucho_partial/paste.md",
        "slug": "SASANG_CLINICAL_P344_2026",
        "isbn": "9788992971706",
        "page": "p.344",
        "call_no": "519.74-10-4-1-2",
        "note": "P1-06 partial_excerpt_only · not_canon until scan hash",
        "anchor_out": str(P344_ANCHOR.relative_to(ROOT)).replace("\\", "/"),
    },
]


def _proxy_exists(slug: str) -> bool:
    return (RAW / f"CHEONYUCHO_PHYSICAL_{slug}_nl_proxy.md").is_file()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-bind even if proxy exists")
    args = ap.parse_args()

    results: list[dict] = []
    for item in KNOWN:
        paste = ROOT / item["paste_file"]
        slug = item["slug"]
        if not paste.is_file():
            results.append({"slug": slug, "ok": False, "error": f"missing paste: {paste}"})
            continue
        if _proxy_exists(slug) and not args.force:
            results.append({"slug": slug, "ok": True, "skipped": True, "reason": "proxy_exists"})
            continue
        if args.dry_run:
            results.append({"slug": slug, "ok": True, "dry_run": True, "paste": str(paste)})
            continue
        cmd = [
            sys.executable,
            str(BIND),
            "--paste-file",
            str(paste),
            "--slug",
            slug,
            "--page",
            item["page"],
            "--note",
            item["note"],
        ]
        if item.get("isbn"):
            cmd.extend(["--isbn", item["isbn"]])
        if item.get("call_no"):
            cmd.extend(["--call-no", item["call_no"]])
        if item.get("anchor_out"):
            cmd.extend(["--anchor-out", str(ROOT / item["anchor_out"])])
        cmd.append("--no-patch-probe")
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        line = next((ln for ln in reversed(tail) if ln.strip().startswith("{")), "{}")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"parse_error": True, "tail": tail[-3:]}
        results.append(
            {
                "slug": slug,
                "ok": proc.returncode == 0 and payload.get("ok") is True,
                "exit_code": proc.returncode,
                "payload": payload,
            }
        )
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "results": results}, ensure_ascii=False))
            return 1

    ok = all(r.get("ok") for r in results)
    if ok and not args.dry_run and any(r.get("ok") and not r.get("skipped") for r in results):
        idx = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_cheonyucho_physical_proxy_index_v1.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if idx.returncode != 0:
            print(json.dumps({"ok": False, "error": "proxy_index_failed", "stderr": idx.stderr[-400:]}))
            return 1
    print(json.dumps({"ok": ok, "bound": sum(1 for r in results if r.get("ok") and not r.get("skipped")), "results": results}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
