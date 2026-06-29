#!/usr/bin/env python3
"""Patch media fact sheet with Path A B2B longform spine product-lane row (FAIL-COMP-004)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACT = ROOT / "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json"
API_MD = ROOT / "docs/final/artifacts/media_fact_sheet_compression_api_v1_latest.md"
ROW_LABEL = "B2B longform spine (product lane)"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_fact() -> dict[str, Any]:
    if not FACT.is_file():
        raise SystemExit("missing fact sheet — run path_a_spine_commercial_defense_chain first")
    return json.loads(FACT.read_text(encoding="utf-8-sig"))


def patch(md: str, fact: dict[str, Any]) -> str:
    p = fact["product_lane"]
    saving = p.get("global_token_saving_percent")
    cases = p.get("case_count")
    parity = p.get("byte_exact_subset_parity")
    cell = (
        f"saving **{saving}%** · byte_exact **{parity}** ({cases}-case longform) · "
        f"`path_a_spine_commercial_defense_fact_sheet_v1_latest.json` · **≠ Track A frozen · ≠ latent bench**"
    )
    md = re.sub(
        r"generated_at_utc: [^\n]+",
        f"generated_at_utc: {_utc()}",
        md,
        count=1,
    )
    row_re = rf"\| {re.escape(ROW_LABEL)} \|[^|]*\|[^|]*\|"
    new_row = f"| {ROW_LABEL} | {cell} | `finance_macro_b2b` spine binary billable · honest GTM only |"
    if re.search(row_re, md):
        return re.sub(row_re, new_row, md, count=1)
    anchor = "| Track A frozen (Golden 40) |"
    if anchor not in md:
        raise SystemExit("anchor row missing in media fact sheet")
    return md.replace(anchor, new_row + "\n" + anchor, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api-md", type=Path, default=API_MD)
    args = ap.parse_args()
    fact = _load_fact()
    text = args.api_md.read_text(encoding="utf-8")
    args.api_md.write_text(patch(text, fact), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "api_md": str(args.api_md),
                "saving_percent": fact["product_lane"].get("global_token_saving_percent"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
