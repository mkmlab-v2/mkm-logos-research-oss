#!/usr/bin/env python3
"""Draft station->farm/zone mapping by station name token rules.

Heuristic only. Output must be human-reviewed before operational use.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


REGION_PATTERNS = [
    r"^(?P<name>[^ ]+군)",
    r"^(?P<name>[^ ]+시)",
    r"^(?P<name>[^ ]+구)",
    r"^(?P<name>[^ ]+읍)",
    r"^(?P<name>[^ ]+면)",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create draft mapping from station name tokens.")
    parser.add_argument(
        "--template-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_template_v1.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_draft_v1.csv",
    )
    parser.add_argument(
        "--farm-prefix",
        default="pilot_farm",
        help="Farm id prefix for draft generation.",
    )
    parser.add_argument(
        "--zone-prefix",
        default="zone",
        help="Zone id prefix for draft generation.",
    )
    return parser.parse_args()


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned.lower() if cleaned else "unknown"


def _extract_region_hint(station: str) -> str:
    s = station.strip()
    for pat in REGION_PATTERNS:
        m = re.search(pat, s)
        if m:
            return m.group("name")
    return s.split(" ")[0] if s else "unknown"


def main() -> int:
    args = _parse_args()
    template_path = Path(args.template_csv)
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template csv: {template_path}")

    df = pd.read_csv(template_path)
    if "agmet_station_name" not in df.columns:
        raise ValueError("Template missing agmet_station_name column")

    draft = df.copy()
    region_hints = draft["agmet_station_name"].fillna("").astype(str).map(_extract_region_hint)
    region_slugs = region_hints.map(_slugify)

    draft["farm_id"] = region_slugs.map(lambda x: f"{args.farm_prefix}_{x}")
    draft["zone_id"] = (
        draft.groupby("farm_id").cumcount() + 1
    ).map(lambda n: f"{args.zone_prefix}_{n:03d}")
    draft["notes"] = (
        "AUTO_DRAFT_FROM_STATION_NAME;REVIEW_REQUIRED;region_hint="
        + region_hints.astype(str)
    )
    draft["is_active"] = False

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    draft.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[ok] draft rows: {len(draft)} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

