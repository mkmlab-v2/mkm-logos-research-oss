#!/usr/bin/env python3
"""Fill HWPX table cells from slots JSON (fill_by_path + disambiguated label_cells)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_hwpx():
    try:
        from hwpx import HwpxDocument  # noqa: PLC0415
        from hwpx.tools.table_navigation import _collect_document_tables  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(
            "python-hwpx not installed. Run: py -m pip install -r scripts/requirements-hwpx-poc.txt"
        ) from exc
    return HwpxDocument, _collect_document_tables


def _clear_and_set_cell_text(
    table: Any,
    row_index: int,
    col_index: int,
    text: str,
    *,
    logical: bool = False,
) -> None:
    """Replace narrative cell body without leaving template hint markup glued to MKM text.

    ``set_cell_text`` alone can leave nested ``<hp:t>`` nodes from the official form;
    Hancom then still shows the long ``※`` instruction block and looks \"unfilled\".
    """
    if logical:
        cell = table._grid_entry(row_index, col_index).cell  # noqa: SLF001 — matches library set_cell_text
    else:
        cell = table.cell(row_index, col_index)
    for paragraph in getattr(cell, "paragraphs", None) or []:
        try:
            paragraph.text = ""
        except Exception:
            pass
    table.set_cell_text(row_index, col_index, text, logical=logical)


def _cell_text(table: Any, row_index: int, col_index: int, *, logical: bool = False) -> str:
    if logical:
        cell = table._grid_entry(row_index, col_index).cell  # noqa: SLF001
    else:
        cell = table.cell(row_index, col_index)
    paras = getattr(cell, "paragraphs", None)
    if paras:
        return "".join(getattr(p, "text", "") or "" for p in paras)
    return getattr(cell, "text", "") or ""


def _prepend_cell_text(
    table: Any,
    row_index: int,
    col_index: int,
    prefix: str,
    *,
    logical: bool = False,
) -> None:
    existing = _cell_text(table, row_index, col_index, logical=logical).strip()
    combined = prefix.strip()
    if existing:
        combined = f"{combined}\n\n{existing}"
    _clear_and_set_cell_text(table, row_index, col_index, combined, logical=logical)


def _pick_match(matches: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any] | None:
    table_index = spec.get("table_index")
    match_index = int(spec.get("match_index", 0))
    row = spec.get("row")
    col = spec.get("col")
    col_min = spec.get("col_min")

    filtered = matches
    if table_index is not None:
        filtered = [m for m in filtered if m.get("table_index") == table_index]
    if row is not None:
        filtered = [
            m
            for m in filtered
            if (m.get("target_cell") or {}).get("row") == row
        ]
    if col is not None:
        filtered = [
            m
            for m in filtered
            if (m.get("target_cell") or {}).get("col") == col
        ]
    if col_min is not None:
        filtered = [
            m
            for m in filtered
            if (m.get("target_cell") or {}).get("col", -1) >= int(col_min)
        ]
    if not filtered:
        return None
    if match_index < 0 or match_index >= len(filtered):
        return None
    return filtered[match_index]


def fill_from_slots(
    hwpx_in: Path,
    slots_path: Path,
    hwpx_out: Path,
) -> dict[str, Any]:
    HwpxDocument, _collect_document_tables = _require_hwpx()
    slots = json.loads(slots_path.read_text(encoding="utf-8"))

    hwpx_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hwpx_in, hwpx_out)
    doc = HwpxDocument.open(str(hwpx_out))
    indexed = _collect_document_tables(doc)

    applied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    fill_by_path = slots.get("fill_by_path") or {}
    if fill_by_path:
        result = doc.fill_by_path({str(k): str(v) for k, v in fill_by_path.items()})
        for item in result.get("applied", []):
            applied.append({"kind": "fill_by_path", **item})
        for item in result.get("failed", []):
            failed.append({"kind": "fill_by_path", **item})

    for entry in slots.get("label_cells") or []:
        label = str(entry.get("label", "")).strip()
        value = str(entry.get("value", ""))
        if not label:
            failed.append({"kind": "label_cells", "reason": "empty label", "entry": entry})
            continue
        search = doc.find_cell_by_label(label)
        matches = search.get("matches") or []
        pick = _pick_match(matches, entry)
        if pick is None:
            failed.append(
                {
                    "kind": "label_cells",
                    "label": label,
                    "reason": "no matching cell",
                    "match_count": search.get("count", 0),
                }
            )
            continue
        ti = int(pick["table_index"])
        tc = pick["target_cell"]
        _clear_and_set_cell_text(
            indexed[ti].table,
            int(tc["row"]),
            int(tc["col"]),
            value,
            logical=True,
        )
        applied.append(
            {
                "kind": "label_cells",
                "label": label,
                "table_index": ti,
                "row": tc["row"],
                "col": tc["col"],
                "value": value,
            }
        )

    for entry in slots.get("table_cells") or []:
        try:
            ti = int(entry["table_index"])
            row = int(entry.get("row", 0))
            col = int(entry.get("col", 0))
            value = str(entry.get("value", ""))
        except (KeyError, TypeError, ValueError):
            failed.append({"kind": "table_cells", "reason": "invalid entry", "entry": entry})
            continue
        if ti < 0 or ti >= len(indexed):
            failed.append(
                {
                    "kind": "table_cells",
                    "reason": "table_index out of range",
                    "table_index": ti,
                    "table_count": len(indexed),
                }
            )
            continue
        try:
            _clear_and_set_cell_text(indexed[ti].table, row, col, value, logical=True)
        except Exception as exc:
            failed.append(
                {
                    "kind": "table_cells",
                    "table_index": ti,
                    "row": row,
                    "col": col,
                    "reason": str(exc),
                }
            )
            continue
        applied.append(
            {
                "kind": "table_cells",
                "table_index": ti,
                "row": row,
                "col": col,
                "value_len": len(value),
            }
        )

    for entry in slots.get("footer_table_cells") or []:
        try:
            ti = int(entry["table_index"])
            row = int(entry.get("row", 0))
            col = int(entry.get("col", 0))
            value = str(entry.get("value", ""))
            mode = str(entry.get("mode", "prepend")).lower()
        except (KeyError, TypeError, ValueError):
            failed.append({"kind": "footer_table_cells", "reason": "invalid entry", "entry": entry})
            continue
        if ti < 0 or ti >= len(indexed):
            failed.append(
                {
                    "kind": "footer_table_cells",
                    "reason": "table_index out of range",
                    "table_index": ti,
                }
            )
            continue
        try:
            table = indexed[ti].table
            if mode == "set":
                _clear_and_set_cell_text(table, row, col, value, logical=True)
            else:
                _prepend_cell_text(table, row, col, value, logical=True)
        except Exception as exc:
            failed.append(
                {
                    "kind": "footer_table_cells",
                    "table_index": ti,
                    "row": row,
                    "col": col,
                    "reason": str(exc),
                }
            )
            continue
        applied.append(
            {
                "kind": "footer_table_cells",
                "table_index": ti,
                "row": row,
                "col": col,
                "mode": mode,
                "value_len": len(value),
            }
        )

    doc.save_to_path(str(hwpx_out))
    markdown = HwpxDocument.open(str(hwpx_out)).export_markdown()
    expected = slots.get("expected_substrings") or [
        str(x.get("value", "")) for x in (slots.get("label_cells") or []) if x.get("value")
    ]
    expected += list((slots.get("fill_by_path") or {}).values())
    missing = [s for s in expected if s and str(s) not in markdown]

    return {
        "hwpx_in": hwpx_in.as_posix(),
        "hwpx_out": hwpx_out.as_posix(),
        "slots_path": slots_path.as_posix(),
        "applied": applied,
        "failed": failed,
        "applied_count": len(applied),
        "failed_count": len(failed),
        "missing_substrings": missing,
        "fill_ok": len(failed) == 0 and not missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hwpx", type=Path, required=True, help="Source .hwpx template")
    ap.add_argument("--slots-json", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report-json", type=Path, default=None)
    args = ap.parse_args()

    result = fill_from_slots(args.hwpx.resolve(), args.slots_json.resolve(), args.out.resolve())
    report = {
        "schema": "fill_hwpx_by_label_cells_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "boundary_ack": "research_only — open in Hancom and verify before K-Startup upload",
        **result,
    }
    out_report = args.report_json or (ROOT / "reports/hwpx_poc/hwpx_label_cells_fill_latest.json")
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fill_ok": report["fill_ok"], "output": report["hwpx_out"]}, ensure_ascii=False))
    return 0 if report["fill_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
