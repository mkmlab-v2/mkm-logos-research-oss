#!/usr/bin/env python3
"""Build minimal HWPX label table template for MKM fill PoC (B-track, research_only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/btrack/hwpx_poc/template_v1.hwpx"
DEFAULT_META = ROOT / "reports/hwpx_poc/build_hwpx_poc_template_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_hwpx():
    try:
        from hwpx import HwpxDocument  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(
            "python-hwpx not installed. Run: py -m pip install -r scripts/requirements-hwpx-poc.txt"
        ) from exc
    return HwpxDocument


def build_template(out_path: Path) -> dict[str, object]:
    HwpxDocument = _require_hwpx()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = HwpxDocument.new()
    doc.add_paragraph("MKM HWPX PoC template v1 [B-track research_only]")
    table = doc.add_table(2, 2)
    table.cell(0, 0).text = "성명:"
    table.cell(1, 0).text = "소속:"
    doc.save_to_path(str(out_path))
    return {"template_path": out_path.as_posix(), "rows": 2, "cols": 2}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_TEMPLATE, help="Template .hwpx path")
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META, help="Build metadata JSON")
    args = ap.parse_args()

    info = build_template(args.out.resolve())
    meta = {
        "schema": "build_hwpx_poc_template_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "boundary_ack": "research_only",
        **info,
    }
    args.meta_json.parent.mkdir(parents=True, exist_ok=True)
    args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
