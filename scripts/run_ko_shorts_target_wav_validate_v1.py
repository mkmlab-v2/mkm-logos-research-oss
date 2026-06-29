#!/usr/bin/env python3
"""Validate one ko shorts target WAV end-to-end from spike artifacts [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_cursor_ide_qa_lib_v1 import CASES, run_case_cursor_qa_v1  # noqa: E402
from scripts.ko_shorts_subtitle_gate_lib_v1 import PROFILES, evaluate_subtitle_gate_v1, refine_segments_for_profile_v1  # noqa: E402
from scripts.ko_shorts_target_wav_lib_v1 import (  # noqa: E402
    qa_case_dict_from_artifacts,
    resolve_target_wav_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_target_wav_validate_v1_latest.json"

TARGET_DEFAULT = "web_pansori"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_target_wav_v1(
    *,
    case_id: str | None = None,
    profile_key: str,
    wav: Path | None = None,
    auto: bool = False,
    refetch_missing: bool = True,
    delegate: bool = False,
    delegation_sidecar: Path | None = None,
) -> dict[str, Any]:
    try:
        resolved = resolve_target_wav_v1(
            wav=wav,
            case_id=case_id,
            auto=auto or (not wav and not case_id and not delegate),
            refetch_missing=refetch_missing,
            delegate=delegate,
            delegation_sidecar=delegation_sidecar,
        )
    except (FileNotFoundError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}

    cid = resolved["case_id"]
    case = next((c for c in CASES if c["case_id"] == cid), None)
    if case is None:
        case = qa_case_dict_from_artifacts(resolved["artifacts"])

    spike_path = ROOT / case["spike_json"]
    wav_rel = resolved["wav_rel"]
    if not spike_path.is_file():
        return {"ok": False, "case_id": cid, "error": "spike_missing", "wav": wav_rel}

    spike = _read_json(spike_path)
    profile = PROFILES[profile_key]
    p1 = list(spike.get("p1_segments") or [])
    refined = refine_segments_for_profile_v1(p1, profile, two_pass=True)
    gate = evaluate_subtitle_gate_v1(refined, profile)
    qa = run_case_cursor_qa_v1(case, profile_key=profile_key)

    checks = qa.get("checks") or {}
    qa_pass = bool(qa.get("ok")) and all(
        bool((checks.get(k) or {}).get("auto_pass"))
        for k in ("p1_anchor_sync", "profile_parent_span", "safe_area_frames", "ass_margin_v")
    )
    orphan = checks.get("orphan_cues") or {}
    timing = spike.get("timing_compare") or spike.get("drift_vs_proportional") or {}
    if not timing and spike.get("compare"):
        timing = spike.get("compare") or {}

    ok = bool(gate.get("gate_pass")) and qa_pass

    return {
        "schema": "ko_shorts_target_wav_validate_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "case_id": cid,
        "profile": profile_key,
        "wav": wav_rel,
        "wav_resolved_via": resolved.get("wav_resolved_via"),
        "proxy_note": "clinical_sim allowlist proxy; not patient audio",
        "gate": {
            "gate_pass": gate.get("gate_pass"),
            "char_gate_pass": gate.get("char_gate_pass"),
            "cps_hard_gate_pass": gate.get("cps_hard_gate_pass"),
            "cps_target_pass": gate.get("cps_target_pass"),
            "mean_cps": gate.get("mean_cps"),
            "segment_count": len(refined),
        },
        "cursor_qa": qa,
        "qa_auto_pass": qa_pass,
        "orphan_count": orphan.get("orphan_count"),
        "drift_pointer": "reports/ko_shorts_timing_compare_v1_latest.json",
        "ok": ok,
        "reproduce": f"py scripts/run_ko_shorts_target_wav_validate_v1.py --case-id {cid} --profile {profile_key}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-id", default=None)
    ap.add_argument("--wav", type=Path, default=None)
    ap.add_argument("--auto", action="store_true", help="default web_pansori + OSS fetch if missing")
    ap.add_argument("--delegate", action="store_true", help="resolve custom WAV from sidecar/env/inbox")
    ap.add_argument("--delegation-sidecar", type=Path, default=None)
    ap.add_argument("--no-refetch", action="store_true")
    ap.add_argument("--profile", default="netflix_v16_pro", choices=list(PROFILES))
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    use_auto = args.auto or (not args.wav and not args.case_id and not args.delegate)
    report = validate_target_wav_v1(
        case_id=args.case_id,
        profile_key=args.profile,
        wav=args.wav,
        auto=use_auto,
        refetch_missing=not args.no_refetch,
        delegate=args.delegate,
        delegation_sidecar=args.delegation_sidecar,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": report.get("ok"), "case_id": report.get("case_id"), "out": str(out).replace("\\", "/")},
            ensure_ascii=False,
        )
    )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
