#!/usr/bin/env python3
"""Audit canonical vs archived copies of prophecy_2026_monthly_kospi_btc_fact_safe_v1.json.

Exit codes:
  0 — canonical file exists and is readable JSON
  1 — canonical missing OR unreadable (when --strict-missing)
  2 — argparse / internal error

Does not modify artifacts unless --write-report is set (writes a small JSON summary).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_REL = Path("docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json")
ARCHIVE_GLOB = "docs/final/artifacts/archive/**/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"

# Hard-coded consumer hints (documentation / operator triage; not runtime wiring).
CONSUMER_HINTS = [
    "scripts/build_a_track_go_nogo_status.py (prophecy_monthly input)",
    "scripts/sync_fact_safe_risk_profile.py (--prophecy default)",
    "scripts/build_daily_execution_insight_brief_v1.py",
    "scripts/run_waiting_queue_monthly_check.ps1 ($monthlyProphecyPath)",
    "projects/bitcoin-trading/ops/windows-rehearsal/ensure_daemon_running.ps1 ($factSafeProphecyPath)",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stat_meta(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "size_bytes": st.st_size,
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


def _read_json_meta(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    meta = data.get("meta") if isinstance(data, dict) else {}
    m = meta if isinstance(meta, dict) else {}
    return {
        "schema": data.get("schema") if isinstance(data, dict) else None,
        "generated_at_utc": m.get("generated_at_utc"),
        "high_reliability_decision": m.get("high_reliability_decision"),
        "price_output_locked": m.get("price_output_locked"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workspace-root",
        type=Path,
        default=ROOT,
        help="Repository root (default: parent of scripts/).",
    )
    ap.add_argument(
        "--write-report",
        type=Path,
        default=None,
        help="Optional path to write JSON summary (e.g. docs/final/artifacts/...).",
    )
    ap.add_argument(
        "--strict-missing",
        action="store_true",
        help="Exit 1 if canonical file is missing (default: still exit 1 for missing).",
    )
    args = ap.parse_args()
    _ = args.strict_missing  # reserved: same as default behavior

    root: Path = args.workspace_root.resolve()
    canonical = (root / CANONICAL_REL).resolve()

    duplicates: list[Path] = sorted(
        {p.resolve() for p in root.glob(ARCHIVE_GLOB) if p.is_file()}
    )
    # Exclude canonical if it appears under archive (should not), and de-dup.
    dup_meta: list[dict[str, Any]] = []
    for p in duplicates:
        if p == canonical:
            continue
        dup_meta.append(
            {
                "path": str(p).replace("\\", "/"),
                "sha256": _sha256(p),
                **_stat_meta(p),
            }
        )

    report: dict[str, Any] = {
        "schema": "prophecy_monthly_path_audit_v1",
        "generated_at_utc": _utc_now(),
        "workspace_root": str(root).replace("\\", "/"),
        "canonical": {
            "path": str(canonical).replace("\\", "/"),
            "exists": canonical.is_file(),
        },
        "duplicates_under_archive": dup_meta,
        "consumer_hints": CONSUMER_HINTS,
        "remediation": [
            "Regenerate canonical outputs (no hand-edit): "
            "`py scripts/generate_2026_monthly_kospi_btc_prophecy.py`",
            "Then refresh governance snapshot: `py scripts/build_a_track_go_nogo_status.py`",
        ],
    }

    issues: list[str] = []
    if not canonical.is_file():
        issues.append("canonical_missing")
        report["canonical"]["readable"] = False
    else:
        report["canonical"]["stat"] = _stat_meta(canonical)
        report["canonical"]["sha256"] = _sha256(canonical)
        try:
            report["canonical"]["json_meta"] = _read_json_meta(canonical)
            report["canonical"]["readable"] = True
        except Exception as exc:
            issues.append(f"canonical_json_error:{exc}")
            report["canonical"]["readable"] = False

    # Compare newest archive duplicate to canonical if both exist.
    if dup_meta and report["canonical"].get("sha256"):
        report["note"] = (
            "If canonical is missing but archive copies exist, treat as path/catalog drift — "
            "regenerate into the canonical path rather than copying archive by hand."
        )

    if args.write_report is not None:
        out = args.write_report
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out}")

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not canonical.is_file():
        return 1
    if not report["canonical"].get("readable"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
