#!/usr/bin/env python3
"""Watch K-Startup official cover PDF drop inbox → merge bundle → readiness (local, B-track).

Human-Tier: does not touch K-Startup portal or checklist G3/G5. Commander drops one PDF into
reports/incoming/kstartup_cover/ (not the whole reports/ tree).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INBOX = ROOT / "reports/incoming/kstartup_cover"
DEFAULT_LOG = ROOT / "reports/opendata_327_cover_ingest_log.jsonl"
BUNDLE_PS1 = ROOT / "scripts/Run-OpenData327FinalUploadBundle_v1.ps1"
READINESS_JSON = ROOT / "reports/opendata_327_submission_readiness_latest.json"

_REJECT_NAME_MARKERS = (
    "draft",
    "part_a_cover_draft",
    "part_b",
    "part_c",
    "part_d",
    "submission_bcd",
    "moksori_ai_opendata327",
    "bcd_merged",
)
_MAX_COVER_MB = 15.0
_MIN_COVER_BYTES = 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ensure_inbox_layout(inbox: Path) -> None:
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "processed").mkdir(exist_ok=True)
    (inbox / "failed").mkdir(exist_ok=True)
    readme = inbox / "README_DROP_OFFICIAL_COVER_HERE.txt"
    if not readme.is_file():
        readme.write_text(
            "K-Startup portal official cover (Part A) PDF only.\n"
            "Drop one file here while watch_submission_cover_ingest_v1.py is running.\n"
            "Do not drop full business-plan bundles or DRAFT covers.\n",
            encoding="utf-8",
        )


def is_candidate_cover_pdf(path: Path) -> tuple[bool, str]:
    if path.suffix.lower() != ".pdf":
        return False, "not_pdf"
    if not path.is_file():
        return False, "missing"
    name = path.name.lower()
    for marker in _REJECT_NAME_MARKERS:
        if marker in name:
            return False, f"rejected_name:{marker}"
    size = path.stat().st_size
    if size < _MIN_COVER_BYTES:
        return False, "too_small"
    if size > _MAX_COVER_MB * 1024 * 1024:
        return False, "too_large"
    return True, "ok"


def wait_file_stable(path: Path, *, stable_seconds: float = 1.5, poll: float = 0.25) -> bool:
    if not path.is_file():
        return False
    last_size = -1
    stable_since: float | None = None
    deadline = time.monotonic() + max(stable_seconds * 4, 30.0)
    while time.monotonic() < deadline:
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size == last_size and size > 0:
            if stable_since is None:
                stable_since = time.monotonic()
            elif time.monotonic() - stable_since >= stable_seconds:
                return True
        else:
            stable_since = None
            last_size = size
        time.sleep(poll)
    return False


def _run_final_bundle(cover_pdf: Path, submit_date_kst: str) -> int:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(BUNDLE_PS1),
        "-OfficialCoverPdf",
        str(cover_pdf.resolve()),
        "-SubmitDateKst",
        submit_date_kst,
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
    return proc.returncode


def _readiness_snapshot() -> dict[str, Any]:
    if not READINESS_JSON.is_file():
        return {}
    return json.loads(READINESS_JSON.read_text(encoding="utf-8-sig"))


def ingest_cover_pdf(
    cover_pdf: Path,
    *,
    inbox: Path,
    submit_date_kst: str,
    log_path: Path,
) -> dict[str, Any]:
    _ensure_inbox_layout(inbox)
    ok, reason = is_candidate_cover_pdf(cover_pdf)
    record: dict[str, Any] = {
        "schema": "opendata_327_cover_ingest_v1",
        "at_utc": _utc_now(),
        "source_pdf": str(cover_pdf.resolve()),
        "candidate_ok": ok,
        "candidate_reason": reason,
    }
    if not ok:
        dest = inbox / "failed" / cover_pdf.name
        if cover_pdf.resolve().parent != dest.resolve().parent:
            shutil.move(str(cover_pdf), str(dest))
        record["moved_to"] = str(dest.relative_to(ROOT))
        record["exit_code"] = 2
        _append_log(log_path, record)
        return record

    if not wait_file_stable(cover_pdf):
        record["exit_code"] = 3
        record["error"] = "file_not_stable"
        _append_log(log_path, record)
        return record

    exit_code = _run_final_bundle(cover_pdf, submit_date_kst)
    record["bundle_exit_code"] = exit_code
    readiness = _readiness_snapshot()
    record["ready_for_kstartup_upload"] = readiness.get("ready_for_kstartup_upload")
    record["ready_blockers"] = readiness.get("ready_for_kstartup_upload_blockers")
    record["cover_a_is_draft"] = readiness.get("cover_a_is_draft")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bucket = inbox / ("processed" if exit_code == 0 else "failed")
    dest = bucket / f"{stamp}_{cover_pdf.name}"
    if cover_pdf.exists():
        shutil.move(str(cover_pdf), str(dest))
    record["moved_to"] = str(dest.relative_to(ROOT))
    record["exit_code"] = exit_code
    _append_log(log_path, record)
    return record


def _list_inbox_pdfs(inbox: Path) -> list[Path]:
    if not inbox.is_dir():
        return []
    return sorted(
        p
        for p in inbox.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    )


def watch_loop(
    inbox: Path,
    *,
    poll_interval: float,
    submit_date_kst: str,
    log_path: Path,
) -> int:
    _ensure_inbox_layout(inbox)
    print(
        json.dumps(
            {
                "watching": str(inbox.relative_to(ROOT)),
                "poll_interval": poll_interval,
                "submit_date_kst": submit_date_kst,
                "log": str(log_path.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    seen: set[str] = set()
    while True:
        for pdf in _list_inbox_pdfs(inbox):
            key = str(pdf.resolve())
            if key in seen:
                continue
            seen.add(key)
            result = ingest_cover_pdf(
                pdf,
                inbox=inbox,
                submit_date_kst=submit_date_kst,
                log_path=log_path,
            )
            print(json.dumps(result, ensure_ascii=False))
        time.sleep(poll_interval)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--watch-dir",
        type=Path,
        default=DEFAULT_INBOX,
        help="Inbox directory (default: reports/incoming/kstartup_cover)",
    )
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--submit-date-kst", default="2026-06-05")
    ap.add_argument("--poll-interval", type=float, default=2.0)
    ap.add_argument("--once", action="store_true", help="Process existing PDFs once and exit")
    ap.add_argument(
        "--ingest-file",
        type=Path,
        help="Process a single PDF path (no watch loop)",
    )
    args = ap.parse_args()
    inbox = args.watch_dir if args.watch_dir.is_absolute() else ROOT / args.watch_dir
    log_path = args.log_jsonl if args.log_jsonl.is_absolute() else ROOT / args.log_jsonl

    if args.ingest_file:
        target = args.ingest_file if args.ingest_file.is_absolute() else ROOT / args.ingest_file
        result = ingest_cover_pdf(
            target,
            inbox=inbox,
            submit_date_kst=args.submit_date_kst,
            log_path=log_path,
        )
        print(json.dumps(result, ensure_ascii=False))
        return int(result.get("exit_code", 1))

    if args.once:
        code = 0
        for pdf in _list_inbox_pdfs(inbox):
            result = ingest_cover_pdf(
                pdf,
                inbox=inbox,
                submit_date_kst=args.submit_date_kst,
                log_path=log_path,
            )
            print(json.dumps(result, ensure_ascii=False))
            if result.get("exit_code", 1) != 0:
                code = int(result["exit_code"])
        return code

    try:
        watch_loop(
            inbox,
            poll_interval=args.poll_interval,
            submit_date_kst=args.submit_date_kst,
            log_path=log_path,
        )
    except KeyboardInterrupt:
        print("\n[watch] stopped", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
