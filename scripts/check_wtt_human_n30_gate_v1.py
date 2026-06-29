#!/usr/bin/env python3
"""WTT human n≥30 collection gate — enrollment slots + optional session JSONL [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENROLLMENT = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_enrollment_template_v1.jsonl"
DEFAULT_PACK = ROOT / "reports/warmth_trigger_pilot_pack_v1_latest.json"
DEFAULT_PROTOCOL = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_protocol_v1.example.json"
DEFAULT_OUT = ROOT / "reports/wtt_human_n30_gate_v1_latest.json"
CHECKLIST_OUT = ROOT / "docs/final/artifacts/wtt_pilot_enrollment_checklist_v1_latest.json"
ACTIVE_TENANT = ROOT / "docs/final/artifacts/wtt_pilot_active_tenant_v1_latest.json"
INTAKE_DIR = ROOT / "data/wtt/intake"
INTERNAL_STEMS = frozenset(
    {
        "wtt-operator-panel-v1",
        "wtt-customer-stub-v1",
        "wtt-solo-internal-v1",
        "wtt-synthetic-spicy-v1",
    }
)

COMPLETED_STATUSES = frozenset({"enrolled", "completed", "session_done", "collected"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_enrollment_completed(path: Path) -> tuple[int, list[str]]:
    if not path.is_file():
        return 0, []
    ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        status = str(row.get("participant_status", "")).lower()
        has_session = bool(row.get("session_id"))
        consent = bool(row.get("consent_ack"))
        if status in COMPLETED_STATUSES or (consent and has_session):
            ids.append(str(row.get("enrollment_id", "")))
    return len(ids), ids


def _count_session_jsonl(path: Path | None) -> int:
    if path is None or not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        labels = set(row.get("labels") or [])
        if (
            row.get("customer_provided")
            and "synthetic_stub" not in labels
            and "synthetic_spicy" not in labels
            and "operator_panel" not in labels
        ):
            count += 1
    return count


def _count_eligible_intake_sessions() -> tuple[int, str | None]:
    """Max customer_provided rows from active tenant + non-internal intake JSONL."""
    best = 0
    best_path: str | None = None
    if ACTIVE_TENANT.is_file():
        active = _load_json(ACTIVE_TENANT)
        rel = active.get("session_jsonl")
        if isinstance(rel, str) and rel.strip():
            path = Path(rel)
            if not path.is_absolute():
                path = ROOT / path
            n = _count_session_jsonl(path)
            if n > best:
                best = n
                best_path = str(path.resolve())
    if INTAKE_DIR.is_dir():
        for path in sorted(INTAKE_DIR.glob("*.jsonl")):
            if path.name.startswith("wtt_pilot_") or path.stem in INTERNAL_STEMS:
                continue
            n = _count_session_jsonl(path)
            if n > best:
                best = n
                best_path = str(path.resolve())
    return best, best_path


def build_checklist(*, target_n: int, collected: int, enrollment_ready: bool) -> dict[str, Any]:
    remaining = max(0, target_n - collected)
    return {
        "schema": "wtt_pilot_enrollment_checklist_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "target_n_participants": target_n,
        "human_sessions_collected": collected,
        "remaining_to_gate": remaining,
        "human_n30_gate_met": collected >= target_n,
        "enrollment_ready": enrollment_ready,
        "steps_ko": [
            "1) 법무·면책 동의서 서명 (protocol ethics.disclaimer_ko)",
            "2) enrollment JSONL 슬롯에 participant_status=enrolled + consent_ack=true",
            "3) 세션 종료 후 session_id + pre/post valence·arousal 기록",
            "4) 마스킹 세션 JSONL을 validate_wtt_pilot_jsonl_v1.py --strict 통과",
            "5) Run-WttPilotIntake_v1.ps1 -CustomerJsonl <path> (AllowStubTemplate 아님)",
            "6) collected>=30 이면 본 스크립트 재실행으로 gate 갱신",
        ],
        "one_click_enrollment_routine": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPilotEnrollmentRoutine_v1.ps1",
        "forbidden": [
            "synthetic_spicy 또는 synthetic_stub을 human_n30 실측으로 집계",
            "operator_panel 운영자 패널을 실고객 human_n30으로 집계",
            "SEND_GATE 해제를 합성 코퍼스만으로 단정",
        ],
    }


def evaluate(
    *,
    enrollment_path: Path,
    pack_path: Path,
    protocol_path: Path,
    human_sessions_jsonl: Path | None,
    sync_pack: bool,
    scan_intake_dir: bool = True,
) -> dict[str, Any]:
    protocol = _load_json(protocol_path) if protocol_path.is_file() else {}
    target_n = int(protocol.get("target_n_participants", 30))

    enroll_n, enroll_ids = _count_enrollment_completed(enrollment_path)
    jsonl_n = _count_session_jsonl(human_sessions_jsonl)
    intake_n, intake_path = _count_eligible_intake_sessions() if scan_intake_dir else (0, None)
    collected = max(enroll_n, jsonl_n, intake_n)
    gate_met = collected >= target_n

    pack = _load_json(pack_path) if pack_path.is_file() else {}
    enrollment_ready = bool(pack.get("pilot_ready_for_enrollment"))

    report = {
        "schema": "wtt_human_n30_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "target_n_participants": target_n,
        "enrollment_completed_slots": enroll_n,
        "human_session_jsonl_rows": jsonl_n,
        "intake_dir_customer_rows": intake_n,
        "intake_dir_best_path": intake_path,
        "human_sessions_collected": collected,
        "human_n30_gate_met": gate_met,
        "enrollment_ready": enrollment_ready,
        "enrollment_completed_ids_sample": enroll_ids[:5],
        "send_gate": "HOLD" if not gate_met else "HOLD",
        "note_ko": (
            f"실측 {collected}/{target_n} — gate_met={gate_met}. "
            "gate 통과해도 counsel·실고객 provenance 없으면 SEND HOLD 유지."
        ),
    }

    if sync_pack and pack_path.is_file():
        pack["human_sessions_collected"] = collected
        pack["human_n30_gate_met"] = gate_met
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["pack_synced"] = True

    checklist = build_checklist(
        target_n=target_n,
        collected=collected,
        enrollment_ready=enrollment_ready,
    )
    return report, checklist


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--enrollment-jsonl", type=Path, default=DEFAULT_ENROLLMENT)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--protocol-json", type=Path, default=DEFAULT_PROTOCOL)
    ap.add_argument("--human-sessions-jsonl", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--checklist-out", type=Path, default=CHECKLIST_OUT)
    ap.add_argument("--sync-pack", action="store_true", default=True)
    ap.add_argument("--no-sync-pack", action="store_true")
    ap.add_argument(
        "--no-intake-scan",
        action="store_true",
        help="Do not count data/wtt/intake customer JSONL (enrollment-only mode).",
    )
    ap.add_argument("--strict", action="store_true", help="Exit 1 if human_n30_gate_met is false.")
    args = ap.parse_args()

    sync = args.sync_pack and not args.no_sync_pack
    report, checklist = evaluate(
        enrollment_path=args.enrollment_jsonl.resolve(),
        pack_path=args.pack_json.resolve(),
        protocol_path=args.protocol_json.resolve(),
        human_sessions_jsonl=args.human_sessions_jsonl.resolve() if args.human_sessions_jsonl else None,
        sync_pack=sync,
        scan_intake_dir=not args.no_intake_scan,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.checklist_out.parent.mkdir(parents=True, exist_ok=True)
    args.checklist_out.write_text(json.dumps(checklist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "collected": report["human_sessions_collected"],
                "target_n": report["target_n_participants"],
                "gate_met": report["human_n30_gate_met"],
            }
        )
    )
    if args.strict and not report["human_n30_gate_met"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
