#!/usr/bin/env python3
"""Export find_cell_by_label inventory for an HWPX form (mapping helper)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS = [
    "창업아이템명",
    "기업명",
    "신청 주관기관명",
    "명     칭",
    "범     주",
    "개요",
    "과제번호",
    "사업 분야",
    "정부지원",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hwpx", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/hwpx_poc/hwpx_form_label_inventory_latest.json")
    ap.add_argument("--labels", nargs="*", default=DEFAULT_LABELS)
    args = ap.parse_args()

    from hwpx import HwpxDocument  # noqa: PLC0415

    doc = HwpxDocument.open(str(args.hwpx.resolve()))
    inventory: dict[str, object] = {}
    for label in args.labels:
        try:
            inventory[label] = doc.find_cell_by_label(label)
        except Exception as exc:
            inventory[label] = {"error": str(exc)}

    out = {
        "schema": "hwpx_form_label_inventory_v1",
        "generated_at_utc": _utc_now(),
        "hwpx": args.hwpx.resolve().as_posix(),
        "labels": inventory,
        "table_map_preview": doc.get_table_map(),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out_json.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
