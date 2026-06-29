#!/usr/bin/env python3
"""Automated checks for CapCut/Vrew manual QA checklist [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_ass_burnin_lib_v1 import segments_from_srt_v1  # noqa: E402
from scripts.media_stt_transcription_lib_v1 import _is_orphan_ending, _is_orphan_prefix  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ko_shorts_manual_tool_qa_verify_v1_latest.json"
CHECKLIST = ROOT / "reports/ko_shorts_manual_tool_qa_checklist_v1_latest.json"
GATE_BENCH = ROOT / "reports/ko_shorts_subtitle_gate_bench_v1_latest.json"
TIMING_COMPARE = ROOT / "reports/ko_shorts_timing_compare_v1_latest.json"
BURNIN_BATCH = ROOT / "reports/ko_shorts_burnin_batch_v1_latest.json"

MP4_PATHS = [
    ROOT / "reports/ko_shorts_burnin_web_deeply_v1_latest.mp4",
    ROOT / "reports/ko_shorts_burnin_web_pansori_v1_latest.mp4",
    ROOT / "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.mp4",
]
ASS_PATHS = [
    ROOT / "reports/ko_shorts_burnin_web_deeply_v1_latest.ass",
    ROOT / "reports/ko_shorts_burnin_web_pansori_v1_latest.ass",
    ROOT / "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.ass",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _collect_subtitle_segments() -> list[dict[str, Any]]:
    segs: list[dict[str, Any]] = []
    for srt_path in [
        ROOT / "reports/ko_shorts_burnin_web_deeply_v1_latest.srt",
        ROOT / "reports/ko_shorts_burnin_web_pansori_v1_latest.srt",
        ROOT / "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.srt",
    ]:
        if not srt_path.is_file():
            continue
        segs.extend(segments_from_srt_v1(srt_path.read_text(encoding="utf-8-sig")))
    return segs


def _check_sync_drift() -> dict[str, Any]:
    doc = _read_json(TIMING_COMPARE)
    if not doc:
        return {"id": "sync_drift", "auto_pass": None, "human_required": True, "error": "timing_compare_missing"}
    cases = list(doc.get("cases") or [])
    drifts = [
        float((c.get("drift_vs_proportional") or {}).get("start_drift_ms_mean") or 0)
        for c in cases
    ]
    return {
        "id": "sync_drift",
        "auto_pass": None,
        "human_required": True,
        "note": "drift is gap metric only; CapCut/Vrew eyeball ±300ms",
        "start_drift_ms_mean_by_case": [
            {"case_id": c.get("case_id"), "ms": (c.get("drift_vs_proportional") or {}).get("start_drift_ms_mean")}
            for c in cases
        ],
        "max_start_drift_ms": max(drifts) if drifts else None,
    }


def _check_orphan_lines(segments: list[dict[str, Any]]) -> dict[str, Any]:
    orphans: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        if _is_orphan_prefix(text) or _is_orphan_ending(text):
            orphans.append({"id": seg.get("id"), "text": text})
    burnin_all_pass = True
    for meta_path in ROOT.glob("reports/ko_shorts_burnin_web_*_v1_latest.json"):
        meta = _read_json(meta_path)
        if meta and not (meta.get("gate") or {}).get("gate_pass"):
            burnin_all_pass = False
            break
    return {
        "id": "orphan_line",
        "auto_pass": len(orphans) == 0,
        "human_required": False,
        "orphan_count": len(orphans),
        "orphans": orphans[:10],
        "burnin_gate_all_pass": burnin_all_pass,
    }


def _check_netflix_cpl() -> dict[str, Any]:
    doc = _read_json(GATE_BENCH)
    if not doc:
        return {"id": "netflix_cpl", "auto_pass": False, "human_required": False, "error": "gate_bench_missing"}
    passes: list[bool] = []
    for case in doc.get("cases") or []:
        gate = ((case.get("profiles") or {}).get("netflix_v16") or {}).get("gate") or {}
        if gate:
            passes.append(bool(gate.get("gate_pass")))
    burnin_passes: list[bool] = []
    for meta_path in ROOT.glob("reports/ko_shorts_burnin_web_*_v1_latest.json"):
        meta = _read_json(meta_path)
        if meta:
            burnin_passes.append(bool((meta.get("gate") or {}).get("gate_pass")))
    return {
        "id": "netflix_cpl",
        "auto_pass": (all(passes) if passes else False) and (all(burnin_passes) if burnin_passes else False),
        "human_required": False,
        "gate_bench_netflix_case_count": len(passes),
        "gate_bench_netflix_pass_count": sum(1 for p in passes if p),
        "burnin_gate_pass_count": sum(1 for p in burnin_passes if p),
        "burnin_case_count": len(burnin_passes),
    }


def _check_safe_area() -> dict[str, Any]:
    missing_mp4 = [p for p in MP4_PATHS if not p.is_file()]
    ass_checks: list[dict[str, Any]] = []
    for ass_path in ASS_PATHS:
        if not ass_path.is_file():
            ass_checks.append({"path": _rel(ass_path), "ok": False, "error": "missing"})
            continue
        text = ass_path.read_text(encoding="utf-8-sig")
        margin_v = None
        m = re.search(r"Style: Default,[^,]+,\d+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,(\d+),", text)
        if m:
            margin_v = int(m.group(1))
        ass_checks.append(
            {
                "path": _rel(ass_path),
                "ok": "PlayResX: 1080" in text and (margin_v is None or margin_v >= 220),
                "margin_v": margin_v,
            }
        )
    return {
        "id": "safe_area",
        "auto_pass": not missing_mp4 and all(c.get("ok") for c in ass_checks),
        "human_required": True,
        "note": "ASS margins auto-checked; MP4 UI overlap needs human Shorts preview",
        "mp4_present": [ _rel(p) for p in MP4_PATHS if p.is_file() ],
        "mp4_missing": [ _rel(p) for p in missing_mp4 ],
        "ass_checks": ass_checks,
    }


def _check_cps_readability() -> dict[str, Any]:
    doc = _read_json(GATE_BENCH)
    if not doc:
        return {"id": "cps_readability", "auto_pass": False, "human_required": True, "error": "gate_bench_missing"}
    hard_fails = 0
    target_fails = 0
    for case in doc.get("cases") or []:
        gate = case.get("gate") or {}
        if gate.get("profile") != "netflix_v16":
            continue
        if not gate.get("cps_hard_gate_pass"):
            hard_fails += 1
        if not gate.get("cps_target_pass"):
            target_fails += 1
    return {
        "id": "cps_readability",
        "auto_pass": hard_fails == 0,
        "human_required": True,
        "note": "hard CPS gate auto; Vrew readability is human",
        "netflix_hard_fail_cases": hard_fails,
        "netflix_target_soft_fail_cases": target_fails,
    }


def _check_scholarly_isolation() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_ko_shorts_scholarly_mode_guard_v1.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "id": "scholarly_mode_isolation",
        "auto_pass": proc.returncode == 0,
        "human_required": False,
        "pytest_exit_code": proc.returncode,
    }


def build_verify_report_v1() -> dict[str, Any]:
    segments = _collect_subtitle_segments()
    checks = [
        _check_sync_drift(),
        _check_orphan_lines(segments),
        _check_netflix_cpl(),
        _check_safe_area(),
        _check_cps_readability(),
        _check_scholarly_isolation(),
    ]
    auto_checks = [c for c in checks if c.get("auto_pass") is not None]
    auto_pass = all(bool(c.get("auto_pass")) for c in auto_checks)
    return {
        "schema": "ko_shorts_manual_tool_qa_verify_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "checklist_source": _rel(CHECKLIST) if CHECKLIST.is_file() else None,
        "auto_pass": auto_pass,
        "human_required_items": [c["id"] for c in checks if c.get("human_required")],
        "checks": checks,
        "reproduce": "py scripts/verify_ko_shorts_manual_tool_qa_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report = build_verify_report_v1()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["auto_pass"],
                "out": _rel(out),
                "human_required": report["human_required_items"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["auto_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
