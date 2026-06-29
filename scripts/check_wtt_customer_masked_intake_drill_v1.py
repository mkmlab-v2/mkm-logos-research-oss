#!/usr/bin/env python3
"""WTT customer-masked intake drill — readiness without synthetic/stub flags ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KIT = ROOT / "docs/final/artifacts/wtt_pilot_target_intake_kit_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/wtt_customer_masked_intake_drill_v1_latest.json"
DEFAULT_STUB = ROOT / "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"
INTAKE_CMD = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 "
    "-TenantId <slug> -SessionJsonl <path/to/customer_masked.jsonl>"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-jsonl", type=Path, default=None, help="Real customer masked JSONL (20-50 rows).")
    ap.add_argument("--kit", type=Path, default=DEFAULT_KIT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--solo-internal-rehearsal",
        action="store_true",
        help="1-person dev: record stub path for internal rehearsal only (not customer_masked).",
    )
    args = ap.parse_args()

    kit: dict[str, Any] = json.loads(args.kit.read_text(encoding="utf-8"))
    session_path = args.session_jsonl.resolve() if args.session_jsonl else None
    solo_internal = bool(args.solo_internal_rehearsal)
    stub_path = DEFAULT_STUB.resolve() if DEFAULT_STUB.is_file() else None

    blockers: list[str] = []
    if session_path is None:
        if solo_internal and stub_path and stub_path.is_file():
            session_path = stub_path
        else:
            blockers.append("customer_masked_jsonl_missing")
    elif not session_path.is_file():
        blockers.append(f"file_not_found:{_rel(session_path)}")

    ready = not blockers and not solo_internal
    solo_rehearsal_ready = solo_internal and session_path is not None and session_path.is_file()
    report = {
        "schema": "wtt_customer_masked_intake_drill_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "intake_kit": _rel(args.kit),
        "session_jsonl": _rel(session_path) if session_path else None,
        "customer_masked_drill_ready": ready,
        "solo_internal_rehearsal_ready": solo_rehearsal_ready,
        "solo_dev": solo_internal,
        "legal_review": "none_operator_self_check" if solo_internal else "counsel_recommended_if_external",
        "blockers": blockers,
        "requirements": {
            "min_sessions": kit.get("session_count_min", 20),
            "max_sessions": kit.get("session_count_max", 50),
            "forbidden_flags": ["AllowSynthetic", "AllowStubTemplate"],
            "labels_required": ["customer_masked", "pii_scrubbed"],
            "labels_forbidden": ["synthetic_spicy", "synthetic_stub", "pilot_template"],
        },
        "one_click_when_file_ready": INTAKE_CMD,
        "counsel_before_send": False if solo_internal else True,
        "external_send_note_ko": (
            "법무 없음(1인). 대외 송부 시 PUBLIC_FACING v1.7 자가 점검·면책 필수."
            if solo_internal
            else "대외 송부 전 법무 검토 권장."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "customer_masked_drill_ready": ready,
                "solo_internal_rehearsal_ready": solo_rehearsal_ready,
                "blockers": blockers,
            }
        )
    )
    if solo_rehearsal_ready:
        return 0
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
