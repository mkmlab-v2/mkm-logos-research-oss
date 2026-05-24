#!/usr/bin/env python3
"""Re-save python-hwpx output through Hancom so the native viewer shows cell text reliably."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _open_hwpx(hwp: object, path: Path) -> None:
    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(path.resolve())
    hwp.HParameterSet.HFileOpenSave.Format = (
        "HWPX" if path.suffix.lower() == ".hwpx" else "HWP"
    )
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)


def _save_as(hwp: object, path: Path, fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    hwp.HAction.GetDefault("FileSaveAs", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(path.resolve())
    hwp.HParameterSet.HFileOpenSave.Format = fmt
    hwp.HAction.Execute("FileSaveAs", hwp.HParameterSet.HFileOpenSave.HSet)
    if not path.is_file() or path.stat().st_size < 1024:
        raise SystemExit(f"Hancom save failed: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--hwpx",
        type=Path,
        default=ROOT / "reports/hwpx_poc/ms_microsoft_ma_jung_filled_v1.hwpx",
    )
    ap.add_argument(
        "--out-hwp",
        type=Path,
        default=ROOT / "reports/hwpx_poc/ms_microsoft_ma_jung_filled_v1.hwp",
    )
    ap.add_argument(
        "--out-hwpx",
        type=Path,
        default=None,
        help="Optional second HWPX path (Hancom round-trip)",
    )
    ap.add_argument(
        "--copy-downloads",
        action="store_true",
        help="Copy .hwp and .hwpx to Downloads 채움본 names",
    )
    ap.add_argument("--text-out", type=Path, default=ROOT / "reports/hwpx_poc/hancom_text_extract_latest.txt")
    ap.add_argument("--visible", action="store_true", help="Show Hancom window while saving")
    args = ap.parse_args()

    try:
        import win32com.client  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit("pywin32 required on Windows") from exc

    src = args.hwpx.resolve()
    if not src.is_file():
        raise SystemExit(f"missing: {src}")

    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
    hwp.SetMessageBoxMode(0x00000000)
    hwp.XHwpWindows.Item(0).Visible = bool(args.visible)

    _open_hwpx(hwp, src)
    text = hwp.GetTextFile("TEXT", "")
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(text, encoding="utf-8")

    _save_as(hwp, args.out_hwp.resolve(), "HWP")
    out_hwpx = args.out_hwpx or src
    if args.out_hwpx:
        _save_as(hwp, out_hwpx.resolve(), "HWPX")

    hwp.Quit()

    meta = {
        "schema": "resave_hwpx_via_hancom_v1",
        "generated_at_utc": _utc_now(),
        "source_hwpx": src.as_posix(),
        "out_hwp": args.out_hwp.resolve().as_posix(),
        "text_len": len(text),
        "has_narrative_enterprise": "엔터프라이즈" in text,
        "has_mkm_trust": "MKM Trust" in text,
    }
    if args.copy_downloads:
        dl = Path.home() / "Downloads"
        hwp_dst = dl / "별첨1-2_마중_사업계획서_MKM_공고329.hwp"
        hwpx_dst = dl / "별첨1-2_마중_사업계획서_MKM_공고329.hwpx"
        shutil.copy2(args.out_hwp.resolve(), hwp_dst)
        shutil.copy2(out_hwpx.resolve(), hwpx_dst)
        meta["downloads_hwp"] = hwp_dst.as_posix()
        meta["downloads_hwpx"] = hwpx_dst.as_posix()

    report = ROOT / "reports/hwpx_poc/resave_hwpx_via_hancom_latest.json"
    report.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
