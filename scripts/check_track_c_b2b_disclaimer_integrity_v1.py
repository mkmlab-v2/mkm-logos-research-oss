#!/usr/bin/env python3
"""Tier A/B disclaimer integrity scan for Track C B2B meeting pack (local parse only)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/track_c_b2b_disclaimer_integrity_v1_latest.json"

# Align with meeting pack index + readiness REQUIRED (+ compression #8).
SCAN_PATHS: tuple[str, ...] = (
    "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md",
    "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md",
    "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md",
    "docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md",
    "docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md",
)

# Per-file Tier A waivers (compression appendix is KPI IR — no Logos NON_GATING required).
TIER_A_WAIVE: dict[str, frozenset[str]] = {
    "track_c_b2b_compression_plugin_appendix_v1_latest.md": frozenset(
        {"non_gating", "core_ip"}
    ),
}

TIER_A_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "no_investment_advice",
            re.compile(
                r"not investment advice|투자자문|투자\s*자문\s*아님|not trade advice|"
                r"investment advice,\s*does not|Risk Warning First|"
                r"decision-support only|의사결정 보조",
                re.I,
            ),
        ),
        (
            "no_buy_sell",
            re.compile(
                r"no buy/sell|buy/sell instructions|매매\s*지시|매매 지시 아님|"
                r"not buy/sell|does not provide buy/sell|— not buy/sell",
                re.I,
            ),
        ),
    ("non_gating", re.compile(r"NON_GATING|\[NON_GATING\]", re.I)),
    (
        "core_ip",
        re.compile(
            r"§9A|core formulas not disclosed|코어.*미공개|산식.*비공개|"
            r"formulas stay server|Commercial Security Gate",
            re.I,
        ),
    ),
)

CANONICAL_FOOTER = re.compile(
    r"Not investment advice\.\s*No buy/sell instructions\.\s*"
    r"Logos layer\s*`?\[?NON_GATING\]?`?\.?\s*"
    r"Core formulas not disclosed\s*\(§9A\)",
    re.I | re.S,
)

ALT_GOVERNANCE_FOOTER = re.compile(
    r"governance-driven risk warning.*not investment advice.*"
    r"(?:does not provide buy/sell|no buy/sell)",
    re.I | re.S,
)

COMPRESSION_FOOTER = re.compile(
    r"Not investment advice\.\s*Bench.*No buy/sell from compression",
    re.I | re.S,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail_fraction(text: str, frac: float = 0.25) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    start = max(0, int(len(lines) * (1.0 - frac)))
    return "\n".join(lines[start:])


def _scan_file(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    name = Path(rel).name
    if not path.is_file():
        return {
            "path": rel,
            "missing": True,
            "tier_a_ok": False,
            "tier_b_ok": False,
            "ok": False,
            "tier_a_missing": [],
            "tier_b_warnings": ["missing_file"],
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    waived = TIER_A_WAIVE.get(name, frozenset())
    has_footer_bundle = bool(
        CANONICAL_FOOTER.search(text)
        or ALT_GOVERNANCE_FOOTER.search(text)
        or COMPRESSION_FOOTER.search(text)
    )
    tier_a_missing: list[str] = []
    for rule_id, pat in TIER_A_RULES:
        if rule_id in waived:
            continue
        if has_footer_bundle and rule_id in ("no_investment_advice", "no_buy_sell"):
            continue
        if not pat.search(text):
            tier_a_missing.append(rule_id)

    tier_b_warnings: list[str] = []
    if "DRAFT_AUTO" not in text and "DRAFT" not in text:
        tier_b_warnings.append("missing_draft_banner")

    tail = _tail_fraction(text)
    has_canonical = bool(CANONICAL_FOOTER.search(text))
    has_alt = bool(ALT_GOVERNANCE_FOOTER.search(text))
    has_compression = bool(COMPRESSION_FOOTER.search(text))
    footer_in_tail = bool(
        CANONICAL_FOOTER.search(tail)
        or ALT_GOVERNANCE_FOOTER.search(tail)
        or COMPRESSION_FOOTER.search(tail)
    )

    if not (has_canonical or has_alt or has_compression):
        tier_b_warnings.append("no_recognized_footer_block")
    elif not footer_in_tail:
        tier_b_warnings.append("footer_not_in_document_tail")

    tier_a_ok = not tier_a_missing
    tier_b_ok = not tier_b_warnings
    return {
        "path": rel,
        "missing": False,
        "tier_a_ok": tier_a_ok,
        "tier_b_ok": tier_b_ok,
        "ok": tier_a_ok,
        "tier_a_missing": tier_a_missing,
        "tier_b_warnings": tier_b_warnings,
        "footer_match": {
            "canonical_index_style": has_canonical,
            "governance_blockquote": has_alt,
            "compression_appendix_style": has_compression,
            "in_tail": footer_in_tail,
        },
        "waived_tier_a": sorted(waived),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT.relative_to(ROOT)).replace("\\", "/"))
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument(
        "--strict-tier-b",
        action="store_true",
        help="Treat Tier B warnings as exit 1 (default: warn only)",
    )
    args = ap.parse_args()

    files = [_scan_file(rel) for rel in SCAN_PATHS]
    tier_a_fail = [f for f in files if not f.get("missing") and not f.get("tier_a_ok")]
    tier_b_warn = [f for f in files if not f.get("missing") and f.get("tier_b_warnings")]
    missing = [f["path"] for f in files if f.get("missing")]

    tier_b_clear = not tier_b_warn
    integrity_ok = not missing and not tier_a_fail
    if args.strict_tier_b and tier_b_warn:
        integrity_ok = False

    doc: dict[str, Any] = {
        "schema": "track_c_b2b_disclaimer_integrity_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "boundary_ack": "Automated disclaimer morphology scan; not legal sign-off.",
        "integrity_ok": integrity_ok,
        "tier_b_clear": tier_b_clear,
        "conditional_tail_fix_cleared": tier_b_clear,
        "ready_for_external_send": False,
        "external_send_note": (
            "legal_human_signoff_required — tier_b_clear alone does not auto-enable send"
        ),
        "tier_a_block_count": len(tier_a_fail),
        "tier_b_warn_count": len(tier_b_warn),
        "missing_files": missing,
        "canonical_footer_reference": (
            "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md "
            "(Disclaimers section)"
        ),
        "files": files,
    }

    out_path = ROOT / args.out_json
    if not args.stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"WROTE: {out_path}")
        print(f"integrity_ok={integrity_ok}")
        print(f"tier_a_block={len(tier_a_fail)} tier_b_warn={len(tier_b_warn)}")
    else:
        print(json.dumps(doc, indent=2, ensure_ascii=False))

    return 0 if integrity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
