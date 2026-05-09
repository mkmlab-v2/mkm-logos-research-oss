#!/usr/bin/env python3
"""Build staged inclusion status report for three-lens fusion features."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_policy_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_status_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    if not policy_path.is_file():
        raise SystemExit(f"Missing policy: {policy_path}")

    policy = _read_json(policy_path)
    rows = policy.get("features") if isinstance(policy.get("features"), list) else []

    report_rows: list[dict[str, Any]] = []
    counts = {"enabled": 0, "shadow": 0, "blocked": 0}
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "shadow").lower()
        if status not in counts:
            status = "shadow"
        counts[status] += 1
        evidence_rel = str(row.get("evidence_path") or "")
        evidence_abs = ROOT / evidence_rel if evidence_rel and evidence_rel != "N/A" else None
        evidence_exists = bool(evidence_abs and evidence_abs.is_file())
        report_rows.append(
            {
                "id": str(row.get("id") or "unknown"),
                "status": status,
                "track": str(row.get("track") or "B_TRACK"),
                "evidence_path": evidence_rel,
                "evidence_exists": evidence_exists,
            }
        )

    ready_enabled = all(r["evidence_exists"] for r in report_rows if r["status"] == "enabled")
    shadow_missing = [r["id"] for r in report_rows if r["status"] == "shadow" and not r["evidence_exists"]]

    payload = {
        "schema": "three_lens_staged_inclusion_status_v1",
        "generated_at_utc": _now(),
        "policy_path": str(policy_path),
        "summary": {
            "enabled_count": counts["enabled"],
            "shadow_count": counts["shadow"],
            "blocked_count": counts["blocked"],
            "enabled_evidence_all_present": ready_enabled,
            "shadow_missing_count": len(shadow_missing),
        },
        "shadow_missing_ids": shadow_missing,
        "rows": report_rows,
        "decision_hint": "GO_STAGED_FUSION" if ready_enabled else "WATCH_EVIDENCE_GAP",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision_hint": payload["decision_hint"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
