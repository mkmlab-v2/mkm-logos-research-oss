#!/usr/bin/env python3
"""BigSet Tier-0 citation lock gate — source URL anchor pass rate [HYPO].

Default gate: pass_rate >= 0.85 → CANDIDATE_RESEARCH (still send_gate HOLD).
Below gate: rows copied to shadow artifact; promotion blocked.

Reproducible (offline, CI):
  py scripts/check_bigset_tier0_citation_lock_v1.py --csv docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/bigset_tier0_citation_lock_v1_latest.json"
DEFAULT_SHADOW = ROOT / "docs/final/artifacts/bigset_tier0_shadow_rows_v1_latest.json"
DEFAULT_MIN_PASS_RATE = 0.85


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _anchor_url(row: dict[str, str]) -> str:
    return str(row.get("citation_lock_anchor") or row.get("source_url") or "").strip()


def _url_locked(url: str, *, offline: bool) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    if offline:
        return True
    try:
        import urllib.request

        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= int(resp.status) < 400
    except Exception:
        return False


def evaluate(
    rows: list[dict[str, str]],
    *,
    min_pass_rate: float,
    offline: bool,
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    locked = 0
    for i, row in enumerate(rows):
        anchor = _anchor_url(row)
        ok = _url_locked(anchor, offline=offline)
        if ok:
            locked += 1
        details.append(
            {
                "row_index": i,
                "conflict_group_id": row.get("conflict_group_id"),
                "school_tier": row.get("school_tier"),
                "citation_lock_anchor": anchor,
                "locked": ok,
            }
        )
    total = len(rows)
    pass_rate = (locked / total) if total else 0.0
    gate_ok = total > 0 and pass_rate >= min_pass_rate
    promotion_mode = "candidate_research" if gate_ok else "shadow_only"
    return {
        "schema": "bigset_tier0_citation_lock_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "offline": offline,
        "min_pass_rate": min_pass_rate,
        "row_count": total,
        "locked_count": locked,
        "pass_rate": round(pass_rate, 6),
        "gate_ok": gate_ok,
        "promotion_mode": promotion_mode,
        "details": details,
        "reproduce": "py scripts/check_bigset_tier0_citation_lock_v1.py --csv <tier0.csv>",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--shadow-out", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    ap.add_argument("--offline", action="store_true", default=True)
    ap.add_argument("--online", action="store_true", help="HEAD-check anchors (network)")
    args = ap.parse_args()

    if not args.csv.is_file():
        print(json.dumps({"ok": False, "error": f"missing csv: {args.csv}"}), file=sys.stderr)
        return 2

    offline = not args.online
    rows = _read_rows(args.csv)
    result = evaluate(rows, min_pass_rate=args.min_pass_rate, offline=offline)

    shadow_rows = []
    promoted_rows = []
    for row, detail in zip(rows, result["details"]):
        if detail["locked"] and result["gate_ok"]:
            row = dict(row)
            row["send_gate_row"] = "CANDIDATE_RESEARCH"
            promoted_rows.append(row)
        else:
            row = dict(row)
            row["send_gate_row"] = "SHADOW"
            shadow_rows.append(row)

    shadow_doc = {
        "schema": "bigset_tier0_shadow_rows_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "gate_ok": result["gate_ok"],
        "pass_rate": result["pass_rate"],
        "rows": shadow_rows if not result["gate_ok"] else [],
        "note_ko": "Shadow console only — citation_lock below gate or row unlock failed.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.shadow_out.parent.mkdir(parents=True, exist_ok=True)
    args.shadow_out.write_text(json.dumps(shadow_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "gate_ok": result["gate_ok"],
                "pass_rate": result["pass_rate"],
                "promotion_mode": result["promotion_mode"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
