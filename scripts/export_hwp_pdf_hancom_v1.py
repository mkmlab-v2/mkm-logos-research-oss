#!/usr/bin/env python3
"""Export HWP/HWPX to PDF via Hancom COM (Windows)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_pdf(src: Path, out_pdf: Path, *, visible: bool = False) -> dict:
    try:
        import win32com.client  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit("pywin32 required") from exc

    if not src.is_file():
        raise SystemExit(f"missing: {src}")

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    if out_pdf.exists():
        out_pdf.unlink()

    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
    hwp.SetMessageBoxMode(0x00000000)
    hwp.XHwpWindows.Item(0).Visible = visible

    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(src.resolve())
    hwp.HParameterSet.HFileOpenSave.Format = "HWPX" if src.suffix.lower() == ".hwpx" else "HWP"
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)

    hwp.HAction.GetDefault("FileSaveAs", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(out_pdf.resolve())
    hwp.HParameterSet.HFileOpenSave.Format = "PDF"
    hwp.HAction.Execute("FileSaveAs", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.Quit()

    if not out_pdf.is_file() or out_pdf.stat().st_size < 1024:
        raise SystemExit(f"PDF export failed: {out_pdf}")

    return {
        "schema": "export_hwp_pdf_hancom_v1",
        "generated_at_utc": _utc(),
        "source": str(src.resolve()),
        "out_pdf": str(out_pdf.resolve()),
        "size_bytes": out_pdf.stat().st_size,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hwp", type=Path, required=True)
    ap.add_argument("--out-pdf", type=Path, required=True)
    ap.add_argument("--visible", action="store_true")
    ap.add_argument("--report-json", type=Path, default=ROOT / "reports/export_hwp_pdf_hancom_latest.json")
    args = ap.parse_args()

    meta = export_pdf(args.hwp.resolve(), args.out_pdf.resolve(), visible=args.visible)
    args.report_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
