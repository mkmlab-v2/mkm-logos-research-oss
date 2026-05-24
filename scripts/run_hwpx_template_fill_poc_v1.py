#!/usr/bin/env python3
"""Fill HWPX template from slots JSON using python-hwpx fill_by_path (B-track PoC)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/btrack/hwpx_poc/template_v1.hwpx"
DEFAULT_SLOTS = ROOT / "data/btrack/hwpx_poc/slots_v1.example.json"
DEFAULT_OUT = ROOT / "reports/hwpx_poc/filled_v1.hwpx"
DEFAULT_REPORT = ROOT / "reports/hwpx_poc/hwpx_template_fill_poc_latest.json"


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


def _load_slots(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    fill = doc.get("fill_by_path")
    if not isinstance(fill, dict) or not fill:
        raise SystemExit(f"slots JSON must contain non-empty fill_by_path: {path}")
    return doc


def fill_template(
    template: Path,
    slots_path: Path,
    out_path: Path,
    *,
    user_template: Path | None = None,
) -> dict[str, Any]:
    HwpxDocument = _require_hwpx()
    slots = _load_slots(slots_path)
    fill_by_path = {str(k): str(v) for k, v in slots["fill_by_path"].items()}

    src = user_template if user_template and user_template.is_file() else template
    if not src.is_file():
        raise SystemExit(f"template missing: {src} (run build_hwpx_poc_template_v1.py first)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    working = out_path.with_suffix(".working.hwpx")
    shutil.copy2(src, working)

    doc = HwpxDocument.open(str(working))
    fill_result = doc.fill_by_path(fill_by_path)
    doc.save_to_path(str(working))
    if out_path.exists():
        out_path.unlink()
    working.rename(out_path)

    markdown = HwpxDocument.open(str(out_path)).export_markdown()
    expected = slots.get("expected_substrings") or list(fill_by_path.values())
    missing = [s for s in expected if str(s) not in markdown]

    return {
        "template_path": src.as_posix(),
        "slots_path": slots_path.as_posix(),
        "output_path": out_path.as_posix(),
        "fill_result": fill_result,
        "markdown_preview": markdown[:2000],
        "expected_substrings": expected,
        "missing_substrings": missing,
        "fill_ok": fill_result.get("failed_count", 1) == 0 and not missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--slots-json", type=Path, default=DEFAULT_SLOTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--user-template",
        type=Path,
        default=None,
        help="Official .hwpx form path (overrides bundled PoC template)",
    )
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    result = fill_template(
        args.template.resolve(),
        args.slots_json.resolve(),
        args.out.resolve(),
        user_template=args.user_template.resolve() if args.user_template else None,
    )
    report = {
        "schema": "hwpx_template_fill_poc_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "boundary_ack": "research_only — human review before any external submission",
        **result,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fill_ok": report["fill_ok"], "output_path": report["output_path"]}, ensure_ascii=False))
    return 0 if report["fill_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
