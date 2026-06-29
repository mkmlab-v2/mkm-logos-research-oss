#!/usr/bin/env python3
"""Pre-counsel copy guardrail scan for Track C B2B meeting pack (no auto-edit)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "track_c_b2b_counsel_copy_scan_v1_latest.json"

SCAN_PATHS: tuple[str, ...] = (
    "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_two_layer_agent_slide_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_two_layer_agent_slide_v1_print.html",
    "docs/final/artifacts/track_c_b2b_internal_rehearsal_runbook_v1_latest.md",
    "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md",
    "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md",
    "docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md",
)

# Lines mentioning forbidden topics in negation/disclaimer context are OK.
NEGATION_MARKERS = (
    "do not",
    "do NOT",
    "does not guarantee",
    "does NOT guarantee",
    "하지 않",
    "보장 아님",
    "금지",
    "forbidden",
    "no headline",
    "no zero-hallucination",
    "no zero hallucination",
    "박지 않",
    "NOT sell",
    "What we do NOT",
    "non-binding",
    "확약 없음",
    "혼용 금지",
    "not auto-merge",
)

# Billing-mode comparison tables reference frozen Track A as baseline — not external headline.
BILLING_COMPARISON_MARKERS = (
    "billing mode",
    "billing-mode",
    "dual-axis",
    "canonical",
    "frozen",
    "multilens_track_a_frozen",
    "track a active",
    "vs track a",
    "rollup",
    "not production sla",
    "observed bench",
    "reference only",
    "promotion gate reference",
)

RULES: list[dict[str, Any]] = [
    {
        "id": "track_a_savings_percent",
        "pattern": re.compile(r"\b47\.5\s*%|\b64\.6\s*%|~47\.5|~64\.6", re.I),
        "severity": "block",
    },
    {
        "id": "lossless_claim",
        "pattern": re.compile(r"무손실|lossless\s+guarant|100\s*%\s*복원", re.I),
        "severity": "block",
    },
    {
        "id": "omniscient_ai",
        "pattern": re.compile(r"전지적|omniscient\s+chat|zero\s+hallucination", re.I),
        "severity": "block",
    },
    {
        "id": "auto_live_trading",
        "pattern": re.compile(
            r"실매매\s*자동\s*승격|auto\s+live[- ]?trading\s+promotion|live\s+trading\s+GO",
            re.I,
        ),
        "severity": "block",
    },
    {
        "id": "guaranteed_returns",
        "pattern": re.compile(r"guaranteed\s+returns|수익\s*보장|always\s+profitable", re.I),
        "severity": "block",
    },
    {
        "id": "internal_path_leak",
        "pattern": re.compile(r"[A-Za-z]:\\workspace|docs/final/artifacts/[a-z0-9_./-]+\.json", re.I),
        "severity": "warn",
        "allow_in_files": (
            "track_c_b2b_meeting_pack_index_v1_latest.md",
            "track_c_b2b_internal_rehearsal_runbook_v1_latest.md",
            "track_c_b2b_two_layer_agent_slide_v1_latest.md",
        ),
    },
]

DRAFT_REQUIRED_FILES = (
    "track_c_b2b_two_layer_agent_slide_v1_latest.md",
    "track_c_logos_b2b_exec_summary_slide_v1_latest.md",
    "track_c_logos_redacted_demo_excerpt_v1_latest.md",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


FORBIDDEN_SECTION_HEADERS = re.compile(
    r"^##\s+(Forbidden|금지|do\s+not\s+(say|claim)|explicit\s+non)",
    re.I,
)


def _forbidden_section_lines(lines: list[str]) -> set[int]:
    """Lines under a 'Forbidden' heading are lists of banned phrases — not claims."""
    blocked: set[int] = set()
    in_section = False
    for i, line in enumerate(lines):
        if FORBIDDEN_SECTION_HEADERS.match(line.strip()):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            in_section = False
            continue
        if in_section and line.strip():
            blocked.add(i + 1)
    return blocked


def _line_negated(line: str) -> bool:
    lower = line.lower()
    return any(m.lower() in lower for m in NEGATION_MARKERS)


def _line_billing_comparison(line: str) -> bool:
    lower = line.lower()
    return any(m.lower() in lower for m in BILLING_COMPARISON_MARKERS)


def _scan_file(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.is_file():
        return {"path": rel, "ok": False, "missing": True, "hits": []}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    forbidden_section = _forbidden_section_lines(lines)
    hits: list[dict[str, Any]] = []
    if Path(rel).name in DRAFT_REQUIRED_FILES and "DRAFT_AUTO" not in text:
        hits.append(
            {
                "rule_id": "missing_draft_banner",
                "severity": "warn",
                "message": "DRAFT_AUTO banner not found",
            }
        )

    for rule in RULES:
        allow_files = rule.get("allow_in_files") or ()
        for i, line in enumerate(lines, start=1):
            if not rule["pattern"].search(line):
                continue
            if i in forbidden_section:
                continue
            if _line_negated(line):
                continue
            if rule["id"] == "track_a_savings_percent" and _line_billing_comparison(line):
                continue
            if Path(rel).name in allow_files and rule["id"] == "internal_path_leak":
                continue
            hits.append(
                {
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "line": i,
                    "excerpt": line.strip()[:200],
                }
            )
    blocking = [h for h in hits if h.get("severity") == "block"]
    return {"path": rel, "ok": not blocking, "missing": False, "hits": hits}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    file_results = [_scan_file(rel) for rel in SCAN_PATHS]
    missing = [r["path"] for r in file_results if r.get("missing")]
    blocking_files = [r["path"] for r in file_results if not r.get("ok") and not r.get("missing")]
    scan_ok = not missing and not blocking_files

    report = {
        "schema": "track_c_b2b_counsel_copy_scan_v1",
        "generated_at_utc": _utc_now(),
        "scan_ok": scan_ok,
        "ready_for_counsel_submission": scan_ok,
        "ready_for_external_send": False,
        "boundary_ack": "Automated pre-counsel scan only; not legal sign-off.",
        "missing_files": missing,
        "blocking_files": blocking_files,
        "files": file_results,
    }

    out_path = ROOT / args.out_json
    if not args.stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.stdout_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"WROTE: {out_path}")
        print(f"scan_ok={scan_ok}")

    return 0 if scan_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
