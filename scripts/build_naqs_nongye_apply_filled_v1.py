#!/usr/bin/env python3
"""Build NAQS 농업경영체등록신청서(농업인용) filled HWPX/HWP from slots JSON."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_BLANK = ROOT / "reports/naqs_apply/nongye_apply_blank.hwpx"
DEFAULT_SLOTS = ROOT / "reports/naqs_apply/nongye_apply_slots_v4.json"
DEFAULT_OUT_HWPX = ROOT / "reports/naqs_apply/nongye_apply_filled_latest.hwpx"
DEFAULT_OUT_HWP = ROOT / "reports/naqs_apply/nongye_apply_filled_latest.hwp"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(hwpx_blank: Path, slots_path: Path, hwpx_out: Path, hwp_out: Path) -> dict:
    from hwpx import HwpxDocument  # noqa: PLC0415

    from fill_hwpx_by_label_cells_v1 import fill_from_slots  # noqa: PLC0415

    slots = json.loads(slots_path.read_text(encoding="utf-8"))
    part1 = {
        **slots,
        "table_cells": [x for x in slots.get("table_cells", []) if x.get("table_index") != 1],
    }
    tmp_slots = hwpx_out.parent / "_slots_part1_tmp.json"
    tmp_slots.write_text(json.dumps(part1, ensure_ascii=False), encoding="utf-8")

    hwpx_out.parent.mkdir(parents=True, exist_ok=True)
    hwpx_work = hwpx_out.parent / "_build_work.hwpx"
    fill_from_slots(hwpx_blank, tmp_slots, hwpx_work)

    doc = HwpxDocument.open(str(hwpx_work))
    doc.save_to_path(str(hwpx_work))

    # Section 2: Hancom cell addressing (rows 7 & 11) — avoids merged-cell ghost layout from HWPX-only fill.
    from fill_naqs_farmland_hancom_v1 import fill_farmland_table  # noqa: PLC0415
    from pyhwpx import Hwp  # noqa: PLC0415

    h = Hwp(visible=False)
    h.open(str(hwpx_work.resolve()))
    farm_stats = fill_farmland_table(h)
    hwp_work = hwp_out.parent / "_build_work.hwp"
    if hwp_work.exists():
        hwp_work.unlink()
    h.save_as(str(hwp_work.resolve()), format="HWP")
    try:
        h.hwp.Quit()
    except Exception:
        pass
    shutil.copy2(hwpx_work, hwpx_out)
    shutil.copy2(hwp_work, hwp_out)

    imcha = int(farm_stats["imcha_sum_m2"])
    crop = int(farm_stats["crop_sum_m2"])

    return {
        "generated_at_utc": _utc_now(),
        "slots": str(slots_path),
        "hwpx_out": str(hwpx_out),
        "hwp_out": str(hwp_out),
        "farmland_fill": "hancom_pyhwpx_rows_7_11",
        "area_ssot_m2": slots.get("area_ssot_m2", 3750),
        "imcha_sum_m2": imcha,
        "crop_sum_m2": crop,
        "area_aligned": imcha == 3750 and crop == 3750,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blank-hwpx", type=Path, default=DEFAULT_BLANK)
    ap.add_argument("--slots", type=Path, default=DEFAULT_SLOTS)
    ap.add_argument("--out-hwpx", type=Path, default=DEFAULT_OUT_HWPX)
    ap.add_argument("--out-hwp", type=Path, default=DEFAULT_OUT_HWP)
    ap.add_argument("--copy-downloads", action="store_true")
    ap.add_argument("--report-json", type=Path, default=ROOT / "reports/naqs_apply/nongye_apply_build_latest.json")
    args = ap.parse_args()

    if not args.blank_hwpx.is_file():
        raise SystemExit(f"blank missing: {args.blank_hwpx} — run convert_hwp_to_hwpx first")

    report = build(args.blank_hwpx.resolve(), args.slots.resolve(), args.out_hwpx.resolve(), args.out_hwp.resolve())
    report["schema"] = "build_naqs_nongye_apply_filled_v1"

    if args.copy_downloads:
        dl = Path.home() / "Downloads"
        copies = [
            (args.out_hwp, "[별지 제1호서식] 농업경영체 등록신청서(농업인용)-수정_채움본.hwp"),
            (args.out_hwpx, "[별지 제1호서식] 농업경영체 등록신청서(농업인용)-수정_채움본.hwpx"),
            (args.out_hwp, "[별지 제1호서식] 농업경영체 등록신청서(농업인용)-수정_채움본_v4.hwp"),
            (args.out_hwpx, "[별지 제1호서식] 농업경영체 등록신청서(농업인용)-수정_채움본_v4.hwpx"),
        ]
        skipped: list[str] = []
        for src, name in copies:
            dst = dl / name
            try:
                shutil.copy2(src, dst)
            except PermissionError:
                skipped.append(str(dst))
        if skipped:
            report["copy_skipped_locked"] = skipped

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("area_aligned") else 1


if __name__ == "__main__":
    raise SystemExit(main())
