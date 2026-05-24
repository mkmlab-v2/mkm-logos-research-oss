#!/usr/bin/env python3
"""Probe farmland table layout in NAQS form via pyhwpx."""
from __future__ import annotations

from pathlib import Path

from pyhwpx import Hwp

BLANK = Path(r"C:\Users\PRO\Downloads\[별지 제1호서식] 농업경영체 등록신청서(농업인용)-수정.hwp")
FALLBACK = Path(__file__).resolve().parents[1] / "reports/naqs_apply/nongye_apply_blank.hwpx"


def _clip() -> str:
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT).strip()
    finally:
        win32clipboard.CloseClipboard()


def dump_table(h: Hwp, table_n: int, rows: int = 12, cols: int = 17) -> list[tuple[int, int, str]]:
    h.get_into_nth_table(table_n)
    grid: list[tuple[int, int, str]] = []
    for r in range(rows):
        h.TableColBegin()
        for c in range(cols):
            h.TableCellBlock()
            h.Run("Copy")
            try:
                t = _clip()
            except Exception:
                t = ""
            grid.append((r, c, t))
            if c < cols - 1:
                h.TableRightCell()
        if r < rows - 1:
            h.TableLowerCell()
    return grid


def main() -> int:
    path = BLANK if BLANK.is_file() else FALLBACK
    h = Hwp(visible=False)
    h.open(str(path))
    for ti in (0, 1, 2):
        print(f"=== table_index {ti} ===")
        grid = dump_table(h, ti, rows=8 if ti == 0 else 12, cols=10 if ti == 0 else 17)
        for r in range(min(10, max(g[0] for g in grid) + 1)):
            parts = []
            for c in (0, 1, 4, 6, 7, 8, 14, 16):
                t = next((x[2] for x in grid if x[0] == r and x[1] == c), "")
                if t:
                    parts.append(f"c{c}={t[:18]!r}")
            if parts:
                print(f"  r{r}", " ".join(parts))
    h.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
