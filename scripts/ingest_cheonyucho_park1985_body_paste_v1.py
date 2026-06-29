#!/usr/bin/env python3
"""Ingest Park1985 NLK body/footnote paste → bind → proxy index → optional fragment mine."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIND = ROOT / "scripts/bind_cheonyucho_physical_anchor_v1.py"
INDEX = ROOT / "scripts/build_cheonyucho_physical_proxy_index_v1.py"
PACKS = ROOT / "scripts/build_notebooklm_lens_source_packs_v1.py"
DEFAULT_INPUT = ROOT / "data/corpus/ijeoma/originals/cheonyucho_partial/park1985_nlk_body_paste.md"
DEFAULT_ANCHOR = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_park1985_v1.json"
PARK1985_CALL = "199.1-이617ㄱ"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _run(cmd: list[str]) -> tuple[int, dict | None]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    line = next((ln for ln in reversed(tail) if ln.strip().startswith("{")), None)
    payload = None
    if line:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"parse_error": True, "tail": tail[-3:]}
    return proc.returncode, payload


def validate_paste(text: str) -> tuple[bool, str | None]:
    stripped = text.strip()
    if stripped.startswith("---"):
        parts = stripped.split("---", 2)
        if len(parts) >= 3:
            stripped = parts[2].strip()
    body = stripped
    if "## Transcript" in stripped:
        body = stripped.split("## Transcript", 1)[1].strip()
        for marker in ("(commander paste below)", "(commander / HTR paste)"):
            if marker in body:
                body = body.split(marker, 1)[-1].strip()
    if body.startswith("_(") or "paste here" in body.lower():
        return False, "transcript section empty — paste 협약 library capture below Transcript"
    if len(body) < 80:
        return False, "transcript too short (<80 chars)"
    if not any(m in body for m in ("闡幽", "천유", "遺稿", "유고", "格致", "濟衆")):
        return False, "missing Park1985 grep markers in transcript (闡幽/천유/遺稿/格致/濟衆)"
    return True, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="UTF-8 body/footnote paste")
    ap.add_argument("--page", default="", help="e.g. p.127 or footnote-12")
    ap.add_argument("--slug", default="", help="default PARK1985_NLK_BODY_<date>")
    ap.add_argument("--call-no", default=PARK1985_CALL)
    ap.add_argument("--run-fragment-mine", action="store_true")
    ap.add_argument("--rebuild-packs", action="store_true")
    ap.add_argument(
        "--set-physical-verified",
        action="store_true",
        help="Human gate only — commander confirms 협약 library page match",
    )
    args = ap.parse_args()

    if not args.input.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"missing paste: {args.input}",
                    "hint": f"Save 협약 library capture to {_rel(args.input)} then re-run",
                },
                ensure_ascii=False,
            )
        )
        return 1

    text = args.input.read_text(encoding="utf-8", errors="replace")
    ok, err = validate_paste(text)
    if not ok:
        print(json.dumps({"ok": False, "error": err, "input": _rel(args.input)}, ensure_ascii=False))
        return 1

    slug = args.slug.strip() or f"PARK1985_NLK_BODY_{_utc()[:10].replace('-', '')}"
    bind_cmd = [
        sys.executable,
        str(BIND),
        "--paste-file",
        str(args.input.resolve()),
        "--slug",
        slug,
        "--call-no",
        args.call_no,
        "--note",
        "P1-01 협약도서관 본문·각주 paste · not_canon until scan hash",
        "--anchor-out",
        str(DEFAULT_ANCHOR),
        "--no-patch-probe",
    ]
    if args.page:
        bind_cmd.extend(["--page", args.page])
    if args.run_fragment_mine:
        bind_cmd.append("--run-fragment-mine")
    if args.set_physical_verified:
        bind_cmd.append("--set-physical-verified")

    code, bind_out = _run(bind_cmd)
    if code != 0 or not bind_out or not bind_out.get("ok"):
        print(json.dumps({"ok": False, "stage": "bind", "bind": bind_out}, ensure_ascii=False))
        return 1

    code, index_out = _run([sys.executable, str(INDEX)])
    if code != 0 or not index_out or not index_out.get("ok"):
        print(json.dumps({"ok": False, "stage": "proxy_index", "index": index_out}, ensure_ascii=False))
        return 1

    packs_out = None
    if args.rebuild_packs:
        code, packs_out = _run([sys.executable, str(PACKS)])
        if code != 0:
            print(json.dumps({"ok": False, "stage": "packs", "packs": packs_out}, ensure_ascii=False))
            return 1

    result = {
        "ok": True,
        "slug": slug,
        "paste_proxy_path": bind_out.get("paste_proxy_path"),
        "anchor": _rel(DEFAULT_ANCHOR),
        "proxy_index": index_out.get("out"),
        "hanja_canon_status": "not_acquired",
        "physical_verified": args.set_physical_verified,
        "warnings": bind_out.get("warnings", []),
        "packs_rebuilt": args.rebuild_packs,
        "reproduce": f"py scripts/ingest_cheonyucho_park1985_body_paste_v1.py --input {_rel(args.input)}",
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
