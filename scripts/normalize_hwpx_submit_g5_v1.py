#!/usr/bin/env python3
"""G5: strip blue notice paragraphs, clear ※ hint cells, force black charPr (OpenData 327 submit)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BLUE_NOTICE_SNIPPET = "파란색 글씨로 작성된 안내"
HINT_CLEAR_CELLS: list[tuple[int, int, int]] = [
    (2, 0, 0),
    (3, 0, 0),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_header_xml(xml: str) -> tuple[str, int]:
    count = len(re.findall(r'textColor="#0000FF"', xml, flags=re.I))
    xml = re.sub(r'textColor="#0000FF"', 'textColor="#000000"', xml, flags=re.I)
    return xml, count


def _remove_blue_notice_paragraphs(xml: str) -> tuple[str, int]:
    removed = 0
    pattern = re.compile(
        r"<hp:p\b[^>]*>.*?" + re.escape(BLUE_NOTICE_SNIPPET) + r".*?</hp:p>",
        re.DOTALL,
    )

    def _sub(_: re.Match[str]) -> str:
        nonlocal removed
        removed += 1
        return ""

    xml = pattern.sub(_sub, xml)
    return xml, removed


def _hint_count_in_xml(xml: str) -> int:
    return xml.count("※")


def _strip_inline_hint_fragments(xml: str) -> tuple[str, int]:
    """Remove ※ tails in hp:t and orphan hint-only runs (e.g. 4-2 header)."""
    removed = 0

    def _clean_hp_t(match: re.Match[str]) -> str:
        nonlocal removed
        text = match.group(1)
        if "※" not in text:
            return match.group(0)
        removed += 1
        kept = text.split("※", 1)[0].rstrip()
        return f"<hp:t>{kept}</hp:t>" if kept else "<hp:t></hp:t>"

    xml = re.sub(r"<hp:t>([^<]*)</hp:t>", _clean_hp_t, xml)
    hint_only_runs = (
        "해당사항 없음",
        "'으로 기재",
        "’으로 기재",
        "으로 기재",
    )
    for hint in hint_only_runs:
        pat = rf"<hp:run[^>]*><hp:t>{re.escape(hint)}</hp:t></hp:run>"
        hits = len(re.findall(pat, xml))
        if hits:
            removed += hits
            xml = re.sub(pat, "", xml)
    return xml, removed


def _repack_dir(src_dir: Path, hwpx_out: Path) -> None:
    hwpx_out.parent.mkdir(parents=True, exist_ok=True)
    if hwpx_out.exists():
        hwpx_out.unlink()
    with zipfile.ZipFile(hwpx_out, "w", zipfile.ZIP_DEFLATED) as zout:
        for file_path in sorted(src_dir.rglob("*")):
            if file_path.is_file():
                arc = file_path.relative_to(src_dir).as_posix()
                zout.write(file_path, arc)


def _clear_hint_cells(hwpx_path: Path) -> int:
    from hwpx import HwpxDocument  # noqa: PLC0415
    from hwpx.tools.table_navigation import _collect_document_tables  # noqa: PLC0415
    from scripts.fill_hwpx_by_label_cells_v1 import _clear_and_set_cell_text  # noqa: PLC0415

    doc = HwpxDocument.open(str(hwpx_path))
    indexed = _collect_document_tables(doc)
    cleared = 0
    for ti, row, col in HINT_CLEAR_CELLS:
        if ti < len(indexed):
            _clear_and_set_cell_text(indexed[ti].table, row, col, "", logical=True)
            cleared += 1
    doc.save_to_path(str(hwpx_path))
    return cleared


def normalize_hwpx(hwpx_in: Path, hwpx_out: Path) -> dict[str, Any]:
    hwpx_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hwpx_in, hwpx_out)
    hint_cells_cleared = _clear_hint_cells(hwpx_out)
    inline_hints_stripped = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with zipfile.ZipFile(hwpx_out, "r") as zin:
            zin.extractall(tmp_dir)

        header_path = tmp_dir / "Contents" / "header.xml"
        section_path = tmp_dir / "Contents" / "section0.xml"
        header_xml = header_path.read_text(encoding="utf-8")
        section_xml = section_path.read_text(encoding="utf-8")
        hints_before = _hint_count_in_xml(section_xml)

        header_xml, blue_charpr_patches = _normalize_header_xml(header_xml)
        section_xml, notice_paragraphs_removed = _remove_blue_notice_paragraphs(section_xml)
        section_xml, inline_hints_stripped = _strip_inline_hint_fragments(section_xml)
        header_path.write_text(header_xml, encoding="utf-8")
        section_path.write_text(section_xml, encoding="utf-8")

        _repack_dir(tmp_dir, hwpx_out)
        section_after = (tmp_dir / "Contents" / "section0.xml").read_text(encoding="utf-8")
        hints_after = _hint_count_in_xml(section_after)

    g5_pass = (
        blue_charpr_patches > 0
        and notice_paragraphs_removed >= 1
        and hints_after == 0
    )
    return {
        "ok": True,
        "hwpx_in": hwpx_in.as_posix(),
        "hwpx_out": hwpx_out.as_posix(),
        "blue_charpr_patches": blue_charpr_patches,
        "notice_paragraphs_removed": notice_paragraphs_removed,
        "hint_cells_cleared": hint_cells_cleared,
        "hint_count_before": hints_before,
        "hint_count_after": hints_after,
        "inline_hints_stripped": inline_hints_stripped,
        "g5_automated_pass": g5_pass,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hwpx-in", type=Path, required=True)
    ap.add_argument("--hwpx-out", type=Path, required=True)
    ap.add_argument(
        "--report-json",
        type=Path,
        default=ROOT / "reports/opendata_327_hwpx_g5_normalize_latest.json",
    )
    args = ap.parse_args()

    result = normalize_hwpx(args.hwpx_in.resolve(), args.hwpx_out.resolve())
    report = {
        "schema": "opendata_327_hwpx_g5_normalize_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "boundary_ack": "automated G5 hygiene — still verify in Hancom before upload",
        **result,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "g5_automated_pass": report.get("g5_automated_pass"),
                "hint_count_after": report.get("hint_count_after"),
                "output": report.get("hwpx_out"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report.get("g5_automated_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
