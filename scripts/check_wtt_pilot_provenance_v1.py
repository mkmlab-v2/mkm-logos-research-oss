#!/usr/bin/env python3
"""Check WTT human provenance ledger vs intake binding ([HYPO] · SEND HOLD)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wtt_pilot_provenance_paths_v1 import (
    DEFAULT_REPORT,
    PROVENANCE_DIR,
    SCHEMA_PATH,
    intake_path_for_tenant,
    provenance_path_for_tenant,
)

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    *,
    tenant_id: str,
    provenance_path: Path,
    intake_path: Path | None,
) -> dict[str, Any]:
    import jsonschema

    issues: list[dict[str, str]] = []
    prov: dict[str, Any] | None = None

    if not provenance_path.is_file():
        issues.append({"code": "missing_provenance", "message": _rel(provenance_path)})
    else:
        prov = _load_json(provenance_path)
        if prov.get("tenant_id") != tenant_id:
            issues.append(
                {
                    "code": "tenant_mismatch",
                    "message": f"provenance tenant {prov.get('tenant_id')!r} != {tenant_id!r}",
                }
            )
        if SCHEMA_PATH.is_file():
            try:
                jsonschema.validate(prov, _load_json(SCHEMA_PATH))
            except jsonschema.ValidationError as exc:
                issues.append({"code": "schema", "message": exc.message})

    intake = intake_path or intake_path_for_tenant(tenant_id)
    intake_exists = intake.is_file()
    intake_lines = 0
    intake_digest = ""
    if intake_exists:
        intake_digest = _sha256(intake)
        intake_lines = len([ln for ln in intake.read_text(encoding="utf-8").splitlines() if ln.strip()])
    else:
        issues.append({"code": "missing_intake", "message": _rel(intake)})

    if prov:
        binding = prov.get("intake_binding") or {}
        if binding.get("session_jsonl") and _rel(intake) != binding.get("session_jsonl"):
            issues.append(
                {
                    "code": "intake_path_mismatch",
                    "message": f"binding {_rel(intake)} vs {binding.get('session_jsonl')}",
                }
            )
        if intake_exists and binding.get("content_sha256") and binding["content_sha256"] != intake_digest:
            issues.append({"code": "sha256_mismatch", "message": "intake content changed since provenance"})
        if binding.get("session_count") and int(binding["session_count"]) != intake_lines:
            issues.append(
                {
                    "code": "session_count_mismatch",
                    "message": f"binding {binding.get('session_count')} vs disk {intake_lines}",
                }
            )

        consent = prov.get("consent_evidence") or {}
        if not (prov.get("human_verified_by") or "").strip():
            issues.append({"code": "human_verified_by", "message": "required"})
        if not (consent.get("source_ref") or "").strip():
            issues.append({"code": "consent_source_ref", "message": "required"})
        if consent.get("re_identification_protection_ack") is not True:
            issues.append({"code": "re_id_ack", "message": "must be true"})

        gov = prov.get("governance") or {}
        if gov.get("send_gate_status") != "HOLD":
            issues.append({"code": "send_gate_status", "message": "must remain HOLD in v1"})

    provenance_gate_ok = len(issues) == 0
    send_release = bool((prov or {}).get("governance", {}).get("send_gate_release_ack"))
    return {
        "schema": "wtt_pilot_provenance_check_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "tenant_id": tenant_id,
        "provenance_path": _rel(provenance_path),
        "intake_jsonl": _rel(intake) if intake_exists else None,
        "intake_session_count": intake_lines,
        "intake_sha256": intake_digest or None,
        "provenance_gate_ok": provenance_gate_ok,
        "send_gate": "HOLD",
        "send_gate_release_ack": send_release,
        "ready_for_external_send": False,
        "issue_count": len(issues),
        "issues": issues,
        "note_ko": "provenance_gate_ok여도 SEND·Track A 승격 자동 해제 없음",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--provenance", type=Path, default=None)
    ap.add_argument("--intake-jsonl", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    prov_path = args.provenance or provenance_path_for_tenant(args.tenant_id)
    report = evaluate(
        tenant_id=args.tenant_id,
        provenance_path=prov_path.resolve(),
        intake_path=args.intake_jsonl.resolve() if args.intake_jsonl else None,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["provenance_gate_ok"],
                "tenant_id": args.tenant_id,
                "issues": report["issue_count"],
            }
        )
    )
    if args.strict and not report["provenance_gate_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
