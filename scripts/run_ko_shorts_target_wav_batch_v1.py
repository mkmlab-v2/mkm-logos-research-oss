#!/usr/bin/env python3
"""Batch target WAV chains — clinical_sim trio + delegated custom [HYPO]."""

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

from scripts.ko_shorts_target_wav_lib_v1 import CLINICAL_SIM_CASES, discover_delegated_wav_v1  # noqa: E402
from scripts.run_ko_shorts_target_wav_chain_v1 import run_target_wav_chain_v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ko_shorts_target_wav_batch_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run_batch_v1(
    *,
    profile: str,
    include_clinical_sim: bool,
    include_delegate: bool,
    skip_burn: bool,
    skip_alignment: bool,
    refetch_missing: bool,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    case_ids: list[str] = list(CLINICAL_SIM_CASES) if include_clinical_sim else []
    if include_delegate:
        case_ids.append("__delegate__")

    for item in case_ids:
        try:
            if item == "__delegate__":
                delegated = discover_delegated_wav_v1()
                if not delegated:
                    runs.append({"case_id": "__delegate__", "ok": False, "error": "delegation_empty"})
                    continue
                report = run_target_wav_chain_v1(
                    wav=None,
                    case_id=None,
                    auto=False,
                    profile=profile,
                    domain_hint=delegated.get("domain_hint"),
                    skip_burn=skip_burn,
                    skip_alignment=skip_alignment,
                    refetch_missing=refetch_missing,
                    delegate=True,
                )
            else:
                report = run_target_wav_chain_v1(
                    wav=None,
                    case_id=item,
                    auto=False,
                    profile=profile,
                    domain_hint=None,
                    skip_burn=skip_burn,
                    skip_alignment=skip_alignment,
                    refetch_missing=refetch_missing,
                    delegate=False,
                )
            runs.append(
                {
                    "case_id": report.get("case_id"),
                    "ok": report.get("ok"),
                    "wav": report.get("wav"),
                    "wav_resolved_via": report.get("wav_resolved_via"),
                    "gate_pass": report.get("gate_pass"),
                    "qa_auto_pass": report.get("qa_auto_pass"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            runs.append({"case_id": item, "ok": False, "error": f"{exc.__class__.__name__}:{exc}"})

    ok_count = sum(1 for r in runs if r.get("ok"))
    return {
        "schema": "ko_shorts_target_wav_batch_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "profile": profile,
        "ok": ok_count == len(runs) and bool(runs),
        "ok_count": ok_count,
        "total": len(runs),
        "runs": runs,
        "reproduce": "py scripts/run_ko_shorts_target_wav_batch_v1.py --include-delegate",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="netflix_v16_pro")
    ap.add_argument("--clinical-sim-only", action="store_true")
    ap.add_argument("--delegate-only", action="store_true")
    ap.add_argument("--include-delegate", action="store_true", help="(deprecated alias) same as default batch")
    ap.add_argument("--skip-burn", action="store_true")
    ap.add_argument("--skip-alignment", action="store_true")
    ap.add_argument("--no-refetch", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    include_clinical = not args.delegate_only
    include_delegate = not args.clinical_sim_only

    report = run_batch_v1(
        profile=args.profile,
        include_clinical_sim=include_clinical,
        include_delegate=include_delegate,
        skip_burn=args.skip_burn,
        skip_alignment=args.skip_alignment,
        refetch_missing=not args.no_refetch,
    )
    if args.clinical_sim_only:
        report["reproduce"] = "py scripts/run_ko_shorts_target_wav_batch_v1.py --clinical-sim-only"
    elif args.delegate_only:
        report["reproduce"] = "py scripts/run_ko_shorts_target_wav_batch_v1.py --delegate-only"

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "ok_count": report["ok_count"], "total": report["total"], "out": _rel(out)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
