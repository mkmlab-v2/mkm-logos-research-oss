#!/usr/bin/env python3
"""Batch ASS burn-in for clinical_sim STT spike corpora [HYPO]."""

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

from scripts.ko_shorts_subtitle_gate_lib_v1 import PROFILE_NETFLIX_V16, PROFILES  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ko_shorts_burnin_batch_v1_latest.json"
BURNIN_CLI = ROOT / "scripts/run_ko_shorts_ass_burnin_v1.py"

CASES = [
    {
        "case_id": "web_deeply",
        "spike_json": "reports/ko_shorts_stt_timing_web_deeply_v1_latest.json",
        "wav": "reports/audio/ko_shorts_web_deeply_read_v1.wav",
        "ass_out": "reports/ko_shorts_burnin_web_deeply_v1_latest.ass",
        "mp4_out": "reports/ko_shorts_burnin_web_deeply_v1_latest.mp4",
        "meta_out": "reports/ko_shorts_burnin_web_deeply_v1_latest.json",
    },
    {
        "case_id": "web_pansori",
        "spike_json": "reports/ko_shorts_stt_timing_web_pansori_v1_latest.json",
        "wav": "reports/audio/ko_shorts_web_pansori_tedxkr_v1.wav",
        "ass_out": "reports/ko_shorts_burnin_web_pansori_v1_latest.ass",
        "mp4_out": "reports/ko_shorts_burnin_web_pansori_v1_latest.mp4",
        "meta_out": "reports/ko_shorts_burnin_web_pansori_v1_latest.json",
    },
    {
        "case_id": "web_youtube_edu",
        "spike_json": "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json",
        "wav": "reports/audio/ko_shorts_web_youtube_edu_v1.wav",
        "ass_out": "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.ass",
        "mp4_out": "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.mp4",
        "meta_out": "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.json",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--profile", choices=list(PROFILES), default=PROFILE_NETFLIX_V16)
    ap.add_argument("--cases", default="all", help="comma list or all")
    ap.add_argument("--skip-burn", action="store_true")
    args = ap.parse_args()

    selected = {c["case_id"] for c in CASES}
    if args.cases != "all":
        selected = {x.strip() for x in args.cases.split(",") if x.strip()}

    results: list[dict[str, Any]] = []
    ok_all = True
    for case in CASES:
        if case["case_id"] not in selected:
            continue
        spike = ROOT / case["spike_json"]
        wav = ROOT / case["wav"]
        if not spike.is_file() or not wav.is_file():
            results.append({"case_id": case["case_id"], "ok": False, "error": "missing_spike_or_wav"})
            ok_all = False
            continue
        cmd = [
            "py",
            str(BURNIN_CLI),
            "--profile",
            args.profile,
            "--spike-json",
            str(spike),
            "--wav",
            str(wav),
            "--ass-out",
            str(ROOT / case["ass_out"]),
            "--mp4-out",
            str(ROOT / case["mp4_out"]),
            "--meta-out",
            str(ROOT / case["meta_out"]),
        ]
        if args.skip_burn:
            cmd.append("--skip-burn")
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        summary: dict[str, Any] = {"case_id": case["case_id"], "exit_code": proc.returncode}
        try:
            summary.update(json.loads(proc.stdout.strip().splitlines()[-1]))
        except Exception:
            summary["stdout_tail"] = proc.stdout[-500:]
            summary["stderr_tail"] = proc.stderr[-500:]
        summary["ok"] = proc.returncode == 0
        results.append(summary)
        ok_all = ok_all and proc.returncode == 0

    report = {
        "schema": "ko_shorts_burnin_batch_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "profile": args.profile,
        "case_count": len(results),
        "ok_count": sum(1 for r in results if r.get("ok")),
        "cases": results,
        "reproduce": "py scripts/run_ko_shorts_ass_burnin_batch_v1.py",
    }
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_all, "out": _rel(out), "ok_count": report["ok_count"]}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
