#!/usr/bin/env python3
"""Interactive human gate: PII scan + y/n approve -> intake JSONL + provenance ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SESSION_SCHEMA = ROOT / "docs/final/schemas/wtt_pilot_session_v1.schema.json"
DEFAULT_ENROLLMENT = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_enrollment_template_v1.jsonl"

sys.path.insert(0, str(ROOT / "scripts"))
from validate_wtt_pilot_jsonl_v1 import scan_pii_in_text, scan_pii_warn_in_text  # noqa: E402
from wtt_pilot_provenance_paths_v1 import (  # noqa: E402
    PROVENANCE_DIR,
    intake_path_for_tenant,
    provenance_path_for_tenant,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def coerce_session_row(
    raw: dict[str, Any], *, idx: int, tenant_id: str, lane: str = "customer_masked"
) -> dict[str, Any]:
    """Normalize draft / legacy shapes to wtt_pilot_session_v1 row."""
    if "turns" in raw and isinstance(raw["turns"], list) and raw["turns"]:
        turns = []
        for t in raw["turns"]:
            role = t.get("role") or t.get("speaker") or "user"
            if role == "customer":
                role = "user"
            turns.append({"role": role, "text": str(t.get("text", ""))[:4000]})
        session_id = str(raw.get("session_id") or f"{tenant_id}-session-{idx:03d}")
    elif raw.get("text"):
        session_id = str(raw.get("session_id") or f"{tenant_id}-session-{idx:03d}")
        turns = [{"role": "user", "text": str(raw["text"])[:4000]}]
    else:
        raise ValueError(f"line {idx}: need turns[] or text field")

    if lane == "operator_panel":
        labels = [
            "masked",
            "not_customer_data",
            "research_only",
            "operator_panel",
            "internal_dogfood",
            "human_gate_approved",
        ]
        customer_provided = False
    else:
        labels = ["masked", "not_customer_data", "research_only", "human_gate_approved"]
        customer_provided = True
    domain = raw.get("domain_tag") or "customer-support-chat"
    if raw.get("labels"):
        labels = list(dict.fromkeys(list(raw["labels"]) + labels))
    return {
        "session_id": session_id,
        "domain_tag": domain,
        "labels": labels,
        "customer_provided": customer_provided,
        "turns": turns,
    }


def pii_hits_for_session(row: dict[str, Any]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for turn in row.get("turns") or []:
        if turn.get("role") == "user":
            text = str(turn.get("text", ""))
            for hit in scan_pii_in_text(text):
                hits.append(hit)
            for hit in scan_pii_warn_in_text(text):
                hits.append(hit)
    return hits


def sync_enrollment_slots(enrollment_path: Path, sessions: list[dict[str, Any]]) -> int:
    if not enrollment_path.is_file():
        return 0
    lines = enrollment_path.read_text(encoding="utf-8").splitlines()
    updated = 0
    out_lines: list[str] = []
    sess_idx = 0
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        if sess_idx < len(sessions):
            row["session_id"] = sessions[sess_idx]["session_id"]
            row["consent_ack"] = True
            row["participant_status"] = "enrolled"
            sess_idx += 1
            updated += 1
        out_lines.append(json.dumps(row, ensure_ascii=False))
    enrollment_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return updated


def build_provenance_doc(
    *,
    tenant_id: str,
    human_verified_by: str,
    consent_type: str,
    consent_source_ref: str,
    intake_path: Path,
    session_count: int,
    content_sha256: str,
    enrollment_mapping: list[dict[str, Any]],
    stats: dict[str, int],
    public_facing_ok: bool,
    lane: str,
) -> dict[str, Any]:
    now = _utc_now()
    return {
        "schema": "wtt_pilot_provenance_v1",
        "tenant_id": tenant_id,
        "generated_at_utc": now,
        "updated_at_utc": now,
        "human_verified_by": human_verified_by,
        "consent_evidence": {
            "type": consent_type,
            "source_ref": consent_source_ref,
            "verified_at_utc": now,
            "re_identification_protection_ack": True,
        },
        "intake_binding": {
            "session_jsonl": _rel(intake_path),
            "session_count": session_count,
            "content_sha256": content_sha256,
        },
        "enrollment_mapping": enrollment_mapping,
        "governance": {
            "counsel_signoff_required": False,
            "public_facing_v17_compliant": public_facing_ok,
            "send_gate_status": "HOLD",
            "send_gate_release_ack": False,
            "panel_lane": "operator_panel" if lane == "operator_panel" else "customer_masked",
            "not_eligible_for_send": lane == "operator_panel",
        },
        "human_gate_sessions": stats,
    }


def run_gate(
    *,
    tenant_id: str,
    source_path: Path,
    human_verified_by: str,
    consent_type: str,
    consent_source_ref: str,
    approve_all: bool,
    min_approve: int,
    sync_enrollment: bool,
    trigger_intake: bool,
    public_facing_ok: bool,
    lane: str,
) -> dict[str, Any]:
    raw_rows = _load_lines(source_path)
    approved: list[dict[str, Any]] = []
    rejected = 0
    reviewed = 0

    print("=" * 52)
    print(" MKM WTT Human Gate Verification v1")
    print("=" * 52)
    print(f"tenant: {tenant_id} | source: {_rel(source_path)}")
    print(f"min approve for intake write: {min_approve}")
    print()

    for idx, raw in enumerate(raw_rows, start=1):
        try:
            row = coerce_session_row(raw, idx=idx, tenant_id=tenant_id, lane=lane)
        except ValueError as exc:
            print(f"[skip] line {idx}: {exc}")
            rejected += 1
            continue

        reviewed += 1
        hits = pii_hits_for_session(row)
        print(f"--- session {idx}/{len(raw_rows)}: {row['session_id']} ---")
        for turn in row["turns"]:
            print(f"  [{turn['role']}] {turn['text'][:200]}")
        if hits:
            print(f"  ⚠ PII scan: {hits}")

        ok = approve_all
        if not approve_all:
            if not sys.stdin.isatty():
                print(">> non-TTY: use --approve-all for batch mode")
                rejected += 1
                continue
            choice = input(">> Approve masking + consent for this session? (y/n): ").strip().lower()
            ok = choice in {"y", "yes"}

        if ok:
            approved.append(row)
            print("  approved")
        else:
            rejected += 1
            print("  rejected")

    intake_path = intake_path_for_tenant(tenant_id)
    intake_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path = provenance_path_for_tenant(tenant_id)
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "tenant_id": tenant_id,
        "reviewed": reviewed,
        "approved": len(approved),
        "rejected": rejected,
        "intake_written": False,
        "provenance_written": False,
        "intake_path": None,
        "provenance_path": None,
    }

    if len(approved) < min_approve:
        result["error"] = f"approved {len(approved)} < min {min_approve}; intake not written"
        print(f"\n[hold] {result['error']}")
        return result

    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in approved) + "\n"
    intake_path.write_text(body, encoding="utf-8", newline="\n")
    digest = _sha256_file(intake_path)

    mapping = [
        {
            "session_id": r["session_id"],
            "consent_ack": True,
            "domain_tag": r.get("domain_tag", "customer-support-chat"),
        }
        for r in approved
    ]
    prov = build_provenance_doc(
        tenant_id=tenant_id,
        human_verified_by=human_verified_by,
        consent_type=consent_type,
        consent_source_ref=consent_source_ref,
        intake_path=intake_path,
        session_count=len(approved),
        content_sha256=digest,
        enrollment_mapping=mapping,
        stats={"reviewed": reviewed, "approved": len(approved), "rejected": rejected},
        public_facing_ok=public_facing_ok,
        lane=lane,
    )
    provenance_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result["intake_written"] = True
    result["provenance_written"] = True
    result["intake_path"] = _rel(intake_path)
    result["provenance_path"] = _rel(provenance_path)

    if sync_enrollment:
        n = sync_enrollment_slots(DEFAULT_ENROLLMENT, approved)
        result["enrollment_slots_synced"] = n
        print(f"\n[enrollment] synced {n} slots")

    # validate strict
    validate_cmd = [
        sys.executable,
        str(ROOT / "scripts/validate_wtt_pilot_jsonl_v1.py"),
        "--jsonl",
        str(intake_path),
        "--min-sessions",
        str(min(min_approve, len(approved))),
        "--strict",
        "--allow-missing-synthetic-labels",
    ]
    if lane == "operator_panel":
        validate_cmd.append("--lane-operator-panel")
    proc = subprocess.run(
        validate_cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    result["validate_exit_code"] = proc.returncode
    if proc.returncode != 0:
        result["error"] = "validate_strict_failed"
        print(proc.stdout or proc.stderr)
        return result

    chk = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_wtt_pilot_provenance_v1.py"),
            "--tenant-id",
            tenant_id,
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    result["provenance_check_exit_code"] = chk.returncode

    print(f"\n[ok] intake: {_rel(intake_path)}")
    print(f"[ok] provenance: {_rel(provenance_path)}")

    if trigger_intake:
        if lane == "operator_panel":
            ps1 = ROOT / "scripts/Run-WttPilotIntake_v1.ps1"
            tip = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                    "-TenantId",
                    tenant_id,
                    "-SessionJsonl",
                    _rel(intake_path),
                    "-AllowOperatorPanel",
                    "-MinSessions",
                    str(min_approve),
                ],
                cwd=str(ROOT),
                check=False,
            )
        else:
            ps1 = ROOT / "scripts/Invoke-WttPilotIntakeAuto_v1.ps1"
            tip = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                    "-SessionJsonl",
                    _rel(intake_path),
                ],
                cwd=str(ROOT),
                check=False,
            )
        result["intake_trigger_exit_code"] = tip.returncode

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--source-jsonl", type=Path, required=True)
    ap.add_argument("--human-verified-by", default="commander")
    ap.add_argument("--consent-type", default="email", choices=["email", "slack_export", "signed_pdf", "contract_clause", "other"])
    ap.add_argument("--consent-source-ref", required=True, help="Path or ref to consent evidence (not committed to git).")
    ap.add_argument("--min-approve", type=int, default=20)
    ap.add_argument(
        "--lane",
        choices=["customer_masked", "operator_panel"],
        default="customer_masked",
        help="operator_panel: internal dogfood; customer_provided=false; not SEND eligible.",
    )
    ap.add_argument("--approve-all", action="store_true", help="Non-interactive: approve every coercible session.")
    ap.add_argument("--sync-enrollment", action="store_true")
    ap.add_argument("--trigger-intake", action="store_true")
    ap.add_argument("--public-facing-ok", action="store_true", help="Operator ack PUBLIC_FACING v1.7 self-check.")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/wtt_human_gate_interactive_v1_latest.json")
    args = ap.parse_args()

    if not args.public_facing_ok and not args.approve_all:
        print("Note: pass --public-facing-ok after PUBLIC_FACING v1.7 self-check (solo dev).")

    result = run_gate(
        tenant_id=args.tenant_id,
        source_path=args.source_jsonl.resolve(),
        human_verified_by=args.human_verified_by,
        consent_type=args.consent_type,
        consent_source_ref=args.consent_source_ref,
        approve_all=args.approve_all,
        min_approve=args.min_approve,
        sync_enrollment=args.sync_enrollment,
        trigger_intake=args.trigger_intake,
        public_facing_ok=args.public_facing_ok,
        lane=args.lane,
    )
    result["schema"] = "wtt_human_gate_interactive_v1"
    result["generated_at_utc"] = _utc_now()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = result.get("intake_written") and result.get("validate_exit_code") == 0
    print(json.dumps({"ok": ok, "approved": result.get("approved")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
