#!/usr/bin/env python3
"""Readiness gate for compression enterprise 1-Pager vs PUBLIC_FACING v1.7."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "docs" / "final" / "artifacts" / "compression_enterprise_executive_summary_v1.md"
PUBLIC = ROOT / "docs" / "final" / "PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
KPI = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"

FORBIDDEN_PATTERNS = [
    (re.compile(r"리콜\s*0\s*%|0\s*%\s*리콜", re.I), "recall_0_pct"),
    (re.compile(r"zero[- ]?liability", re.I), "zero_liability"),
    (re.compile(r"환각\s*(제거|없음|0)", re.I), "hallucination_eradication"),
    (re.compile(r"7680|7,680", re.I), "7680_sweep_unverified"),
    (re.compile(r"\b8\.2\s*ms\b", re.I), "8.2ms_unverified"),
    (re.compile(r"세계\s*유일|0\.1\s*%\s*스타트업", re.I), "hype_superlative"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-json",
        default="reports/compression_enterprise_summary_readiness_v1_latest.json",
    )
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    checks: list[dict[str, object]] = []
    missing: list[str] = []

    for label, path in [
        ("summary", SUMMARY),
        ("public_facing", PUBLIC),
        ("kpi_summary", KPI),
    ]:
        ok = path.is_file()
        checks.append({"id": f"file:{path.name}", "ok": ok})
        if not ok:
            missing.append(str(path.relative_to(ROOT)))

    text = SUMMARY.read_text(encoding="utf-8") if SUMMARY.is_file() else ""
    draft_ok = "[DRAFT]" in text
    checks.append({"id": "banner:DRAFT", "ok": draft_ok})

    forbidden_hits: list[str] = []
    for pat, code in FORBIDDEN_PATTERNS:
        if pat.search(text):
            forbidden_hits.append(code)
    checks.append({"id": "forbidden_phrases_absent", "ok": len(forbidden_hits) == 0, "hits": forbidden_hits})

    disclaimer_ok = all(
        x in text.lower()
        for x in ("not investment advice", "jaccard", "bench")
    )
    checks.append({"id": "disclaimers_present", "ok": disclaimer_ok})

    ready = not missing and draft_ok and not forbidden_hits and disclaimer_ok
    out = {
        "schema": "compression_enterprise_summary_readiness_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ready_for_external_send": False,
        "ready_for_internal_oem_draft": ready,
        "checks": checks,
        "missing_paths": missing,
        "note": "ready_for_external_send stays false until legal sign-off (RQ-009 alignment).",
    }

    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = json.dumps({"ready_internal": ready, "exit_code": 0 if ready else 1}, ensure_ascii=False)
    if args.stdout_only:
        print(payload)
    else:
        print(f"WROTE: {out_path}")
        print(payload)
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
