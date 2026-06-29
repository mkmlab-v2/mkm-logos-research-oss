#!/usr/bin/env python3
"""Polluted bench: fixture replay or live YouTube URL ingest + closure [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_youtube_transcript_v0 import fetch_youtube_transcript_v0
from scripts.load_media_polluted_bench_ssot_v0 import (
    load_media_polluted_bench_ssot_v0,
    read_fixture_transcript,
    resolve_polluted_bench_youtube_url,
    transcript_fingerprint_v0,
)
from scripts.parse_youtube_transcript_segments_v0 import split_youtube_transcript_blocks

DEFAULT_OUT = ROOT / "reports/media_polluted_bench_live_ingest_v0_latest.json"
FULL_CHAIN = ROOT / "scripts/run_media_youtube_full_ingest_chain_v1.py"
CLOSURE = ROOT / "scripts/verify_handoff_closure_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    return proc.returncode, tail[-1] if tail else ""


def run_polluted_bench_ingest(
    *,
    ssot_path: Path | None = None,
    force_fixture: bool = False,
    task_id: str | None = None,
    verify_closure: bool = True,
) -> dict[str, Any]:
    ssot = load_media_polluted_bench_ssot_v0(ssot_path)
    tid = task_id or str(ssot.get("default_task_id") or "20260621-YT-FULL")
    keywords = list(ssot.get("fingerprint_keywords") or [])
    min_hits = int(ssot.get("fingerprint_min_hits") or 4)

    fixture_text = read_fixture_transcript(ssot)
    fixture_fp = transcript_fingerprint_v0(fixture_text, keywords, min_hits=min_hits)
    fixture_blocks = len(split_youtube_transcript_blocks(fixture_text))

    url = None if force_fixture else resolve_polluted_bench_youtube_url(ssot)
    mode = "fixture_replay"
    live_fetch: dict[str, Any] | None = None
    live_fp: dict[str, Any] | None = None
    fingerprint_match: dict[str, Any] | None = None

    chain_cmd: list[str]
    if url:
        mode = "live_youtube"
        live_fetch = fetch_youtube_transcript_v0(url, languages=("ko", "en"), dry_run=False)
        if not live_fetch.get("ok"):
            return {
                "schema": "media_polluted_bench_live_ingest_v0",
                "generated_at_utc": _utc_now(),
                "research_only": True,
                "send_gate": "HOLD",
                "hypothesis_class": "HYPO",
                "mode": mode,
                "task_id": tid,
                "youtube_url": url,
                "ok": False,
                "error": live_fetch.get("error"),
                "live_fetch": live_fetch,
                "fixture_fingerprint": fixture_fp,
            }

        live_text = str(live_fetch.get("text") or "")
        live_fp = transcript_fingerprint_v0(live_text, keywords, min_hits=min_hits)
        live_blocks = len(split_youtube_transcript_blocks(live_text))
        shared_hits = [
            k for k, ok in (live_fp.get("hits") or {}).items() if ok and (fixture_fp.get("hits") or {}).get(k)
        ]
        fingerprint_match = {
            "live_pass": live_fp.get("pass"),
            "fixture_pass": fixture_fp.get("pass"),
            "shared_keyword_hits": shared_hits,
            "shared_hit_count": len(shared_hits),
            "block_count_live": live_blocks,
            "block_count_fixture": fixture_blocks,
            "block_ratio_live_over_fixture": round(live_blocks / fixture_blocks, 4) if fixture_blocks else None,
        }
        if not live_fp.get("pass"):
            return {
                "schema": "media_polluted_bench_live_ingest_v0",
                "generated_at_utc": _utc_now(),
                "research_only": True,
                "send_gate": "HOLD",
                "hypothesis_class": "HYPO",
                "mode": mode,
                "task_id": tid,
                "youtube_url": url,
                "ok": False,
                "error": "live_fingerprint_failed",
                "live_fingerprint": live_fp,
                "fixture_fingerprint": fixture_fp,
                "fingerprint_match": fingerprint_match,
            }

        chain_cmd = [
            sys.executable,
            str(FULL_CHAIN),
            "--youtube-url",
            url,
            "--task-id",
            tid,
        ]
    else:
        fixture_path = ROOT / str(ssot.get("fixture_transcript"))
        chain_cmd = [
            sys.executable,
            str(FULL_CHAIN),
            "--input",
            str(fixture_path),
            "--task-id",
            tid,
        ]

    chain_code, chain_tail = _run(chain_cmd)
    closure_code = None
    closure_tail = None
    if verify_closure and chain_code == 0:
        closure_code, closure_tail = _run(
            [
                sys.executable,
                str(CLOSURE),
                "--task-id",
                tid,
                "--dry-run",
            ]
        )

    ok = chain_code == 0 and (closure_code in (0, None) if verify_closure else True)
    return {
        "schema": "media_polluted_bench_live_ingest_v0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "mode": mode,
        "task_id": tid,
        "youtube_url": url,
        "ok": ok,
        "fixture_fingerprint": fixture_fp,
        "live_fingerprint": live_fp,
        "fingerprint_match": fingerprint_match,
        "live_fetch": {k: v for k, v in (live_fetch or {}).items() if k != "text"} if live_fetch else None,
        "chain": {"exit_code": chain_code, "tail": chain_tail},
        "closure": {"exit_code": closure_code, "tail": closure_tail} if verify_closure else None,
        "handoff_markdown": f"reports/handoff_workers/HW-{tid}-LOGOS_CLIP.md",
        "diff_report": "reports/media_youtube_ingest_diff_v0_latest.json",
        "ssot": _rel(ssot_path or ROOT / "tests/fixtures/media_polluted_bench_youtube_ssot_v1.json"),
        "reproduce": "py scripts/run_media_polluted_bench_live_ingest_v0.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot", type=Path, default=None)
    ap.add_argument("--live", action="store_true", help="Require MKM_POLLUTED_BENCH_YOUTUBE_URL (fail if unset)")
    ap.add_argument("--fixture", action="store_true", help="Force fixture replay even if URL env is set")
    ap.add_argument("--task-id", default=None)
    ap.add_argument("--skip-closure", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.live and not args.fixture:
        ssot = load_media_polluted_bench_ssot_v0(args.ssot)
        if not resolve_polluted_bench_youtube_url(ssot):
            env_key = ssot.get("youtube_url_env") or "MKM_POLLUTED_BENCH_YOUTUBE_URL"
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "youtube_url_missing",
                        "hint": f"set {env_key}=https://youtu.be/VIDEO_ID",
                    },
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2

    doc = run_polluted_bench_ingest(
        ssot_path=args.ssot,
        force_fixture=bool(args.fixture),
        task_id=args.task_id,
        verify_closure=not args.skip_closure,
    )

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": doc.get("ok"),
                "mode": doc.get("mode"),
                "report": _rel(out),
                "task_id": doc.get("task_id"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
