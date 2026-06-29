#!/usr/bin/env python3
"""Macro YouTube transcript -> diff -> handoff -> Logos bridge sidecar [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = ROOT / "tests/fixtures/media_youtube_macro_trump_fed_ssot_v1.json"
DIFF = ROOT / "scripts/build_media_youtube_ingest_diff_report_v0.py"
BRIDGE = ROOT / "scripts/build_media_youtube_logos_bridge_sidecar_v1.py"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _join_keywords(items: list[str]) -> str:
    return ",".join(x.strip() for x in items if x and str(x).strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--skip-topology-ingest", action="store_true")
    args = ap.parse_args()

    ssot_path = args.ssot if args.ssot.is_absolute() else ROOT / args.ssot
    if not ssot_path.is_file():
        print(json.dumps({"ok": False, "error": "ssot_missing", "path": str(ssot_path)}), file=sys.stderr)
        return 1

    ssot = _read_json(ssot_path)
    transcript = ROOT / str(ssot.get("fixture_transcript") or "")
    if not transcript.is_file():
        print(json.dumps({"ok": False, "error": "transcript_missing", "path": str(transcript)}), file=sys.stderr)
        return 1

    task_id = str(ssot.get("default_task_id") or "MEDIA-MACRO")
    theme_kws = _join_keywords(list(ssot.get("theme_keywords") or []))
    neg_kws = _join_keywords(list(ssot.get("negative_keywords") or []))
    ml_kws = _join_keywords(list(ssot.get("multilens_keywords") or []))

    diff_cmd = [
        sys.executable,
        str(DIFF),
        "--input",
        str(transcript),
        "--theme",
        str(ssot.get("theme") or "macro YT ingest"),
        "--wav-source",
        str(ssot.get("youtube_url") or "fixture://youtube_macro_v1"),
        "--theme-keywords",
        theme_kws,
        "--negative-keywords",
        neg_kws,
        "--multilens-keywords",
        ml_kws,
        "--merge-min-chars",
        str(ssot.get("merge_min_chars") or 650),
        "--merge-max-chars",
        str(ssot.get("merge_max_chars") or 1300),
        "--task-id",
        task_id,
        "--chain-handoff",
    ]
    proc = subprocess.run(diff_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode or 1

    bridge_cmd = [
        sys.executable,
        str(BRIDGE),
        "--ssot",
        str(ssot_path),
        "--write-topology-seed",
    ]
    if not args.skip_topology_ingest:
        bridge_cmd.append("--ingest-topology")

    proc2 = subprocess.run(bridge_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc2.returncode != 0:
        print(proc2.stderr or proc2.stdout, file=sys.stderr)
        return proc2.returncode or 2

    print(
        json.dumps(
            {
                "ok": True,
                "task_id": task_id,
                "transcript": str(transcript.relative_to(ROOT)).replace("\\", "/"),
                "diff_tail": (proc.stdout or "").strip(),
                "bridge_tail": (proc2.stdout or "").strip(),
                "reproduce": "py scripts/run_media_youtube_macro_ingest_chain_v1.py",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
