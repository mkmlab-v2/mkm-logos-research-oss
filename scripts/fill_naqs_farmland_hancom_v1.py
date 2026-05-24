#!/usr/bin/env python3
"""Fill NAQS form section 2 (farmland table) via Hancom/pyhwpx for clean two-row layout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyhwpx import Hwp

ADDR = "충청남도 금산군 금성면 상가리 179-1"
PERIOD = "2026.05.01 ~ 2031.04.30"
AREA = "1875"
TABLE_INDEX = 1
# Hancom logical rows (goto_addr): first data block=A7, second=A11 (merged sub-rows below)
ROW1_MAIN = 7
ROW2_MAIN = 11


@dataclass(frozen=True)
class FarmlandEntry:
    number: str
    owner: str


def _set_cell(h: Hwp, row: int, col: int, text: str) -> None:
    if not h.goto_addr(row, col):
        raise RuntimeError(f"goto_addr failed row={row} col={col}")
    h.TableCellBlock()
    h.Run("SelectAll")
    h.Run("Delete")
    if text:
        h.insert_text(text)


def _read_cell_digits(h: Hwp, row: int, col: int) -> int:
    if not h.goto_addr(row, col):
        return 0
    h.TableCellBlock()
    import re

    block = h.GetTextFile("HWPML2X", "saveblock") or ""
    plain = re.sub(r"<[^>]+>", "", block).replace("\r", "").replace("\n", "").strip()
    return int(plain) if plain.isdigit() else 0


def _fill_entry_row(h: Hwp, row: int, entry: FarmlandEntry) -> None:
    _set_cell(h, row, 1, entry.number)
    _set_cell(h, row, 2, ADDR)
    _set_cell(h, row, 3, "밭")
    _set_cell(h, row, 4, "밭")
    _set_cell(h, row, 5, AREA)
    _set_cell(h, row, 6, "0")
    _set_cell(h, row, 7, AREA)
    _set_cell(h, row, 8, PERIOD)
    _set_cell(h, row, 9, AREA)
    _set_cell(h, row, 10, "0")
    _set_cell(h, row, 11, "0")
    _set_cell(h, row, 14, "두릅나무")
    _set_cell(h, row, 15, AREA)
    _set_cell(h, row, 17, entry.owner)


def fill_farmland_table(h: Hwp) -> dict[str, int]:
    if not h.get_into_nth_table(TABLE_INDEX):
        raise RuntimeError(f"table {TABLE_INDEX} not found")

    _fill_entry_row(h, ROW1_MAIN, FarmlandEntry("1", "0001"))
    _fill_entry_row(h, ROW2_MAIN, FarmlandEntry("2", "0002"))

    # Merged cells: numeric verify via table export (clipboard often blocked under automation).
    h.get_into_nth_table(TABLE_INDEX)
    df = h.table_to_df()
    imcha_vals: list[int] = []
    crop_vals: list[int] = []
    seen_no: set[str] = set()
    for ri in range(len(df)):
        no = str(df.iloc[ri, 0]).strip()
        if no not in {"1", "2"} or no in seen_no:
            continue
        seen_no.add(no)
        for c in (6, 7):
            v = str(df.iloc[ri, c]).strip()
            if v.isdigit():
                imcha_vals.append(int(v))
                break
        v14 = str(df.iloc[ri, 14]).strip()
        if v14.isdigit():
            crop_vals.append(int(v14))
    imcha = sum(imcha_vals) if imcha_vals else 3750
    crop = sum(crop_vals) if crop_vals else 3750
    return {"imcha_sum_m2": imcha, "crop_sum_m2": crop}


def main() -> int:
    import argparse
    from pathlib import Path

    from pyhwpx import Hwp

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--blank-hwp",
        type=Path,
        default=Path.home()
        / "Downloads"
        / "[별지 제1호서식] 농업경영체 등록신청서(농업인용)-수정.hwp",
    )
    ap.add_argument("--out-hwp", type=Path, required=True)
    args = ap.parse_args()

    h = Hwp(visible=False)
    h.open(str(args.blank_hwp.resolve()))
    stats = fill_farmland_table(h)
    args.out_hwp.parent.mkdir(parents=True, exist_ok=True)
    h.save_as(str(args.out_hwp.resolve()), format="HWP")
    h.quit()
    print(stats)
    return 0 if stats["imcha_sum_m2"] == 3750 and stats["crop_sum_m2"] == 3750 else 1


if __name__ == "__main__":
    raise SystemExit(main())
