#!/usr/bin/env python3
"""Biblical-polemic YouTube fixture -> diff -> handoff -> Logos bridge [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = ROOT / "tests/fixtures/media_youtube_biblical_polemic_ssot_v1.json"
DIFF = ROOT / "scripts/build_media_youtube_ingest_diff_report_v0.py"
BRIDGE = ROOT / "scripts/build_media_youtube_logos_bridge_sidecar_v1.py"
OVERLAP = ROOT / "scripts/eval_media_youtube_overlap_gate_v1.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_media_youtube_overlap_gate_v1 import (  # noqa: E402
    eval_tier_a_overlap_gate,
    write_overlap_report,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _join_keywords(items: list[str]) -> str:
    return ",".join(x.strip() for x in items if x and str(x).strip())


def _artifact_path(ssot: dict[str, Any], key: str, default: str) -> Path:
    artifacts = ssot.get("artifacts") or {}
    rel = str(artifacts.get(key) or default)
    return ROOT / rel


def _validate_ingest(diff_report: dict[str, Any]) -> dict[str, Any]:
    ingest = diff_report.get("ingest") or {}
    scholarly = list(ingest.get("scholarly_top3") or [])
    debunked_in_lane = int(ingest.get("debunked_in_scholarly_lane") or 0)
    scholarly_debunked = [
        s for s in scholarly if str(s.get("provenance_hint") or "") == "debunked_fake"
    ]
    debunked_bottom = list(ingest.get("debunked_bottom3") or [])
    debunked_bottom_ok = all(
        str(s.get("provenance_hint") or "") == "debunked_fake" for s in debunked_bottom
    ) if debunked_bottom else True
    return {
        "debunked_in_scholarly_lane": debunked_in_lane,
        "scholarly_lane_clean": debunked_in_lane == 0 and not scholarly_debunked,
        "debunked_bottom3_all_fake": debunked_bottom_ok,
        "provenance_counts": ingest.get("provenance_counts") or {},
        "segment_count": ingest.get("segment_count"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--skip-topology-ingest", action="store_true")
    ap.add_argument("--skip-validation", action="store_true")
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

    task_id = str(ssot.get("default_task_id") or "20260621-YT-BIBLICAL")
    theme_kws = _join_keywords(list(ssot.get("theme_keywords") or []))
    neg_kws = _join_keywords(list(ssot.get("negative_keywords") or []))
    ml_kws = _join_keywords(list(ssot.get("multilens_keywords") or []))
    diff_out = _artifact_path(ssot, "diff_report", "reports/media_youtube_ingest_diff_biblical_polemic_v1_latest.json")
    stt_out = _artifact_path(ssot, "stt_json", "reports/forensics/stt_transcription_biblical_polemic_v1_latest.json")
    bridge_out = _artifact_path(
        ssot,
        "bridge",
        "docs/final/artifacts/media_youtube_logos_bridge_biblical_polemic_v1_latest.json",
    )
    baseline = ROOT / str(ssot.get("baseline_stt_fixture") or DEFAULT_SSOT.parent / "media_stt_transcription_polluted_bench_v1.json")
    overlap_out = _artifact_path(
        ssot,
        "overlap_report",
        "reports/media_youtube_baseline_overlap_biblical_polemic_v1_latest.json",
    )
    gate_cfg = dict(ssot.get("overlap_gate_v1") or {})
    overlap_window = float(gate_cfg.get("overlap_window_sec") or 120.0)

    diff_cmd = [
        sys.executable,
        str(DIFF),
        "--input",
        str(transcript),
        "--theme",
        str(ssot.get("theme") or "biblical polemic YT ingest"),
        "--wav-source",
        str(ssot.get("youtube_url") or "fixture://youtube_transcript_polluted_full_v0"),
        "--target-suite",
        str(ssot.get("target_suite") or "CapCut & AntiGravity [POLLUTED_BENCH_v2]"),
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
        "--out",
        str(diff_out),
        "--write-stt-json",
        str(stt_out),
        "--baseline",
        str(baseline),
        "--overlap-window-sec",
        str(overlap_window),
        "--chain-handoff",
    ]
    proc = subprocess.run(diff_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode or 1

    validation: dict[str, Any] | None = None
    overlap_report: dict[str, Any] | None = None
    if not args.skip_validation and diff_out.is_file():
        diff_doc = _read_json(diff_out)
        validation = _validate_ingest(diff_doc)
        if not validation.get("scholarly_lane_clean"):
            print(json.dumps({"ok": False, "error": "scholarly_lane_debunked", "validation": validation}), file=sys.stderr)
            return 3
        if gate_cfg:
            overlap_report = eval_tier_a_overlap_gate(
                diff_doc,
                gate_cfg,
                ssot_path=str(ssot_path.relative_to(ROOT)).replace("\\", "/"),
            )
            write_overlap_report(
                overlap_report,
                overlap_out,
                diff_report_rel=str(diff_out.relative_to(ROOT)).replace("\\", "/"),
            )
            if not overlap_report.get("tier_a_pass"):
                print(
                    json.dumps(
                        {"ok": False, "error": "tier_a_overlap_gate_failed", "checks": overlap_report.get("checks")},
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                )
                return 4

    bridge_cmd = [
        sys.executable,
        str(BRIDGE),
        "--ssot",
        str(ssot_path),
        "--diff-report",
        str(diff_out),
        "--stt-json",
        str(stt_out),
        "--out-bridge",
        str(bridge_out),
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
                "diff_report": str(diff_out.relative_to(ROOT)).replace("\\", "/"),
                "bridge": str(bridge_out.relative_to(ROOT)).replace("\\", "/"),
                "overlap_report": str(overlap_out.relative_to(ROOT)).replace("\\", "/"),
                "validation": validation,
                "tier_a_pass": overlap_report.get("tier_a_pass") if overlap_report else None,
                "overlap_checks": overlap_report.get("checks") if overlap_report else None,
                "diff_tail": (proc.stdout or "").strip(),
                "bridge_tail": (proc2.stdout or "").strip(),
                "reproduce": str(ssot.get("reproduce") or "py scripts/run_media_youtube_biblical_ingest_chain_v1.py"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
