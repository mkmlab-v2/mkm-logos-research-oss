#!/usr/bin/env python3
"""Build tier-tagged LIT_REVIEW MD from IJEOMA_SECONDARY_PROXY_v1.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROXY = ROOT / "docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json"
OUT = ROOT / "docs/research/IJEOMA_SECONDARY_PROXY_LIT_REVIEW_2026-06-26.md"

TIER_ORDER = [
    "T0_workspace_canon",
    "T0_partial_paste",
    "T1_secondary_pdf",
    "T1_bibliographic",
    "hypo_guard",
    "unverified_guard",
]

TIER_LABEL = {
    "T0_workspace_canon": "T0 · 동의수세보원 workspace 정본",
    "T0_partial_paste": "T0 partial · 격치고 commander paste",
    "T1_secondary_pdf": "T1 · 의사학 PDF (list/quote)",
    "T1_bibliographic": "T1 · 서지·게이트 메타",
    "hypo_guard": "Guard · [HYPO] / catalog dispute",
    "unverified_guard": "Guard · [UNVERIFIED]",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_md(proxy: dict) -> str:
    lines = [
        "# 이제마 SECONDARY_PROXY LIT_REVIEW (tier-tagged)",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD` · `canon_status: not_acquired`",
        "",
        "**SSOT JSON:** `docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json`",
        "",
        "## Executive",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        "| Primary fulltext substitute? | **No** |",
        "| Proxy role | grep-verified excerpts + explicit UNVERIFIED guards |",
        "| 천유초 火剋金 | **[UNVERIFIED]** — separate from DSSBW canon facts |",
        "",
        "## Tier index",
        "",
    ]
    summary = proxy.get("summary", {})
    for tier, count in summary.get("by_source_tier", {}).items():
        lines.append(f"- `{tier}`: {count} fragments")

    frags = proxy.get("fragments", [])
    by_tier: dict[str, list] = {t: [] for t in TIER_ORDER}
    for f in frags:
        tier = f.get("source_tier", "other")
        by_tier.setdefault(tier, []).append(f)

    for tier in TIER_ORDER:
        group = by_tier.get(tier, [])
        if not group:
            continue
        lines.extend(["", f"## {TIER_LABEL.get(tier, tier)}", ""])
        for f in group:
            vid = f.get("verification_status", "")
            tag = f" `[{vid}]`" if vid else ""
            lines.append(f"### {f['id']} · `{f.get('layer')}`{tag}")
            lines.append("")
            if f.get("quote_hanja"):
                lines.append(f"- **quote_hanja:** {f['quote_hanja']}")
            if f.get("quote_ko"):
                lines.append(f"- **quote_ko:** {f['quote_ko']}")
            lines.append(f"- **source:** {f.get('source_literature')}")
            if f.get("source_path"):
                lines.append(f"- **path:** `{f['source_path']}`")
            if f.get("line_range"):
                lines.append(f"- **line_range:** {f['line_range']}")
            lines.append(f"- **context:** {f.get('context_hint')}")
            lines.append("")

    lines.extend(
        [
            "## Reproduce",
            "",
            "```bash",
            "py scripts/build_ijeoma_secondary_proxy_lit_review_v1.py",
            "py scripts/merge_ijeoma_secondary_proxy_to_fragment_ledger_v1.py",
            "py scripts/check_cheonyucho_acquisition_gate_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proxy", type=Path, default=PROXY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.proxy.is_file():
        raise SystemExit(f"missing proxy: {args.proxy}")

    proxy = json.loads(args.proxy.read_text(encoding="utf-8-sig"))
    args.out.write_text(build_md(proxy), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.relative_to(ROOT)).replace("\\", "/")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
