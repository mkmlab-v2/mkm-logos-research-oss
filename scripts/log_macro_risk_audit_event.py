#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.6}
# Balance: 91
# Purpose: Append Macro Risk API audit event with evidence hash retention.
# Keywords: audit, jsonl, retention, evidence hash, macro risk

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESPONSE = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_smoke_latest.json"
DEFAULT_AUDIT_JSONL = ROOT / "reports" / "macro_risk" / "audit" / "macro_risk_audit_log_v1.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "macro_risk_audit_log_summary_latest.json"
DEFAULT_RETENTION_DAYS = 90


def _read_json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Expected object json: {path}")
    return doc


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return "UNAVAILABLE_ARTIFACT_HASH"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_iso_utc(v: str) -> datetime | None:
    try:
        if v.endswith("Z"):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    path.write_text(data, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append macro risk audit event and enforce retention.")
    p.add_argument("--response", type=Path, default=DEFAULT_RESPONSE)
    p.add_argument("--audit-jsonl", type=Path, default=DEFAULT_AUDIT_JSONL)
    p.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    p.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    response_path = args.response if args.response.is_absolute() else (ROOT / args.response)
    audit_path = args.audit_jsonl if args.audit_jsonl.is_absolute() else (ROOT / args.audit_jsonl)
    summary_path = args.summary_out if args.summary_out.is_absolute() else (ROOT / args.summary_out)
    retention_days = max(1, int(args.retention_days))

    response = _read_json(response_path)
    now = datetime.now(timezone.utc)

    evidence = response.get("evidence_ref") or {}
    evidence_path_rel = str(evidence.get("artifact_path") or "")
    evidence_path_abs = (ROOT / evidence_path_rel) if evidence_path_rel else None
    evidence_hash_in_response = str(evidence.get("artifact_hash_sha256") or "")
    evidence_hash_local = _sha256_file(evidence_path_abs) if evidence_path_abs else "UNAVAILABLE_ARTIFACT_HASH"

    row = {
        "schema": "macro_risk_audit_log_v1",
        "ts_utc": now.isoformat().replace("+00:00", "Z"),
        "client_request_id": response.get("request_id"),
        "asset_scope": response.get("asset_scope"),
        "decision_state": response.get("decision_state"),
        "risk_warning_level": response.get("risk_warning_level"),
        "confidence_band": response.get("confidence_band"),
        "recommended_operator_posture": response.get("recommended_operator_posture"),
        "evidence_ref": {
            "artifact_path": evidence_path_rel,
            "artifact_hash_sha256_response": evidence_hash_in_response,
            "artifact_hash_sha256_local": evidence_hash_local,
            "hash_match": bool(evidence_hash_in_response and evidence_hash_in_response == evidence_hash_local),
        },
    }

    rows = _load_jsonl(audit_path)
    rows.append(row)

    cutoff = now - timedelta(days=retention_days)
    kept: list[dict[str, Any]] = []
    for r in rows:
        ts = str(r.get("ts_utc") or "")
        dt = _parse_iso_utc(ts)
        if dt is None:
            continue
        if dt >= cutoff:
            kept.append(r)

    _write_jsonl(audit_path, kept)

    summary = {
        "schema": "macro_risk_audit_log_summary_v1",
        "ts_utc": now.isoformat().replace("+00:00", "Z"),
        "audit_log_path": str(audit_path),
        "retention_days": retention_days,
        "rows_after_retention": len(kept),
        "latest_event": row,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"audit_log: PASS -> {audit_path}")
    print(f"audit_summary: PASS -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
