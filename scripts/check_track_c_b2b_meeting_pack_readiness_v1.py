#!/usr/bin/env python3
"""Pre-send readiness gate for Track C B2B meeting pack (local, no network)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


REQUIRED = [
    "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md",
    "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md",
    "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md",
    "docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md",
    "docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md",
]

OPTIONAL = [
    "docs/final/artifacts/track_c_b2b_logos_multi_orbit_appendix_v1_latest.md",
    "docs/final/artifacts/logos_multi_orbit_showroom_pack_v1_latest.json",
]

FORBIDDEN_IN_DEMO = [
    re.compile(r"[A-Za-z]:\\workspace", re.I),
    re.compile(r"docs/final/artifacts/[a-z0-9_./-]+\.(json|md)", re.I),
]


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-json",
        default="reports/track_c_b2b_meeting_pack_readiness_v1_latest.json",
    )
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    root = _root()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    missing: list[str] = []
    checks: list[dict[str, object]] = []

    for rel in REQUIRED:
        ok = (root / rel).is_file()
        checks.append({"id": f"file:{rel}", "ok": ok})
        if not ok:
            missing.append(rel)

    optional_missing: list[str] = []
    for rel in OPTIONAL:
        ok = (root / rel).is_file()
        checks.append({"id": f"optional:{rel}", "ok": ok, "required": False})
        if not ok:
            optional_missing.append(rel)

    demo_path = root / "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md"
    slide_path = root / "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md"
    demo_text = demo_path.read_text(encoding="utf-8") if demo_path.is_file() else ""
    slide_text = slide_path.read_text(encoding="utf-8") if slide_path.is_file() else ""

    draft_ok = "DRAFT_AUTO" in demo_text and "DRAFT_AUTO" in slide_text
    checks.append({"id": "banner:DRAFT_AUTO", "ok": draft_ok})

    leak_hits: list[str] = []
    for pat in FORBIDDEN_IN_DEMO:
        if pat.search(demo_text):
            leak_hits.append(pat.pattern)
    checks.append({"id": "demo:no_path_leaks", "ok": not leak_hits, "patterns_matched": leak_hits})

    non_gating_ok = "NON_GATING" in demo_text or "[NON_GATING]" in demo_text
    checks.append({"id": "demo:non_gating_mentioned", "ok": non_gating_ok})

    ready = not missing and draft_ok and not leak_hits and non_gating_ok
    report = {
        "schema": "track_c_b2b_meeting_pack_readiness_v1",
        "generated_at_utc": generated_at,
        "ready_for_internal_meeting": ready,
        "ready_for_external_send": False,
        "external_send_note": "legal_sign_off_required — DRAFT_AUTO artifacts only",
        "missing_files": missing,
        "optional_missing_files": optional_missing,
        "checks": checks,
    }

    out_path = root / args.out_json
    if not args.stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.stdout_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"WROTE: {out_path}")
        print(f"ready_for_internal_meeting={ready}")

    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
