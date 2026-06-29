#!/usr/bin/env python3
"""Compact OpenData 327 HWPX spacing via Hancom (pyhwpx): shrink empty rows, drop empty tables."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BANNER_RE = re.compile(
    r"^\s*\d+\.\s|혁신성|시장성|과제 해결방안|팀 구성|기타|과제 제시|이미지",
    re.I,
)
GRID_HEADER_MARKERS = ("순번", "수상일", "대회", "직급", "구성 상태")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cell_plain(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val)).strip()


def _df_plain(df) -> list[list[str]]:
    rows: list[list[str]] = []
    for r in range(len(df)):
        rows.append([_cell_plain(df.iloc[r, c]) for c in range(len(df.columns))])
    return rows


def _is_empty_table(rows: list[list[str]]) -> bool:
    return not any(any(c for c in row) for row in rows)


def _is_banner_table(rows: list[list[str]]) -> bool:
    if not rows or len(rows) > 2:
        return False
    joined = " ".join(" ".join(row) for row in rows).strip()
    if not joined:
        return False
    non_empty = [c for row in rows for c in row if c]
    if len(non_empty) == 1 and BANNER_RE.search(non_empty[0]):
        return True
    if len(rows) == 1 and len(non_empty) == 1:
        return True
    left = rows[0][0] if rows[0] else ""
    rest = [c for row in rows for c in row[1:] if c]
    return bool(left) and not rest and (BANNER_RE.search(left) or len(left) < 40)


def _is_grid_header_only(rows: list[list[str]]) -> bool:
    if len(rows) < 2:
        return False
    header = " ".join(rows[0])
    if not any(m in header for m in GRID_HEADER_MARKERS):
        return False
    body = rows[1:]
    return not any(any(c for c in row) for row in body)


def _collect_table_ctrls(h) -> list[Any]:
    ctrls: list[Any] = []
    ctrl = h.hwp.HeadCtrl
    while ctrl:
        if ctrl.UserDesc == "표":
            ctrls.append(ctrl)
        ctrl = ctrl.Next
    return ctrls


def _shrink_current_row(h, height_mm: float) -> None:
    try:
        h.set_row_height(height_mm, as_="mm")
    except Exception:
        pass


def _delete_extra_grid_rows(h, data_rows: int) -> int:
    deleted = 0
    for _ in range(data_rows):
        try:
            if h.goto_addr(2, 0):
                h.TableSubtractRow()
                deleted += 1
        except Exception:
            break
    return deleted


def compact_hwpx(hwpx_in: Path, hwpx_out: Path, *, visible: bool = False) -> dict[str, Any]:
    try:
        from pyhwpx import Hwp
    except ImportError as exc:
        raise SystemExit("pyhwpx required: pip install pyhwpx") from exc

    import pandas as pd  # noqa: PLC0415

    h = Hwp(visible=visible)
    h.open(str(hwpx_in.resolve()))
    actions: list[dict[str, Any]] = []

    ctrls = _collect_table_ctrls(h)
    for ti in range(len(ctrls) - 1, -1, -1):
        if not h.get_into_nth_table(ti):
            continue
        try:
            df = h.table_to_df(ti)
        except Exception as exc:
            actions.append({"table_index": ti, "action": "skip", "reason": str(exc)})
            continue

        rows = _df_plain(df)
        label = " ".join(" ".join(r) for r in rows)[:80]

        if _is_empty_table(rows):
            try:
                ctrl = ctrls[ti]
                h.delete_ctrl(ctrl)
                actions.append({"table_index": ti, "action": "delete_empty_table", "preview": label})
            except Exception as exc:
                actions.append({"table_index": ti, "action": "delete_failed", "error": str(exc)})
            continue

        if _is_grid_header_only(rows):
            deleted = _delete_extra_grid_rows(h, len(rows) - 1)
            actions.append(
                {
                    "table_index": ti,
                    "action": "trim_grid_rows",
                    "rows_deleted": deleted,
                    "preview": label,
                }
            )
            continue

        if _is_banner_table(rows):
            h.get_into_nth_table(ti)
            for r in range(len(rows)):
                for c in range(len(rows[r])):
                    if hasattr(h, "goto_addr") and h.goto_addr(r + 1, c + 1):
                        _shrink_current_row(h, 7.0 if rows[r][c] else 4.0)
            actions.append({"table_index": ti, "action": "shrink_banner", "preview": label})
            continue

        # Content / overview: shrink rows that are empty but tall
        shrunk = 0
        h.get_into_nth_table(ti)
        for r in range(len(rows)):
            row_text = " ".join(rows[r]).strip()
            if not row_text:
                if hasattr(h, "goto_addr") and h.goto_addr(r + 1, 1):
                    _shrink_current_row(h, 3.0)
                    shrunk += 1
            elif len(row_text) < 120 and len(rows[r]) > 1:
                if hasattr(h, "goto_addr") and h.goto_addr(r + 1, 2):
                    _shrink_current_row(h, 8.0)
                    shrunk += 1
        if shrunk:
            actions.append({"table_index": ti, "action": "shrink_sparse_rows", "rows": shrunk})

    hwpx_out.parent.mkdir(parents=True, exist_ok=True)
    h.save_as(str(hwpx_out.resolve()), format="HWPX")
    h.quit()

    return {
        "ok": True,
        "hwpx_in": hwpx_in.as_posix(),
        "hwpx_out": hwpx_out.as_posix(),
        "tables_seen": len(ctrls),
        "actions": actions,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--hwpx-in",
        type=Path,
        default=Path.home() / "Downloads" / "(붙임2)_AI+OpenData_사업계획서_목소리_채움본.hwpx",
    )
    ap.add_argument(
        "--hwpx-out",
        type=Path,
        default=ROOT / "reports/opendata_327_official_filled_v4_compact.hwpx",
    )
    ap.add_argument("--report-json", type=Path, default=ROOT / "reports/opendata_327_hwpx_compact_latest.json")
    ap.add_argument("--visible", action="store_true")
    args = ap.parse_args()

    if not args.hwpx_in.is_file():
        raise SystemExit(f"missing: {args.hwpx_in}")

    result = compact_hwpx(args.hwpx_in.resolve(), args.hwpx_out.resolve(), visible=args.visible)
    report = {
        "schema": "opendata_327_hwpx_compact_v1",
        "generated_at_utc": _utc_now(),
        **result,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": report["hwpx_out"], "actions": len(report["actions"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
