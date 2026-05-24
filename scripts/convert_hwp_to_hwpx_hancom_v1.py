#!/usr/bin/env python3
"""Convert .hwp to .hwpx via Hancom HWPFrame HAction (Windows, local only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data/btrack/hwpx_poc/inbox"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def convert_hwp_to_hwpx(src: Path, out: Path) -> dict[str, object]:
    try:
        import win32com.client  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit("pywin32 required on Windows for Hancom COM conversion") from exc

    if not src.is_file():
        raise SystemExit(f"HWP not found: {src}")

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
    hwp.SetMessageBoxMode(0x00000000)

    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(src.resolve())
    hwp.HParameterSet.HFileOpenSave.Format = "HWP"
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)

    hwp.HAction.GetDefault("FileSaveAs", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(out.resolve())
    hwp.HParameterSet.HFileOpenSave.Format = "HWPX"
    hwp.HAction.Execute("FileSaveAs", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.Quit()

    if not out.is_file() or out.stat().st_size < 1024:
        raise SystemExit(f"HWPX conversion failed or empty output: {out}")

    return {
        "source_hwp": src.as_posix(),
        "output_hwpx": out.as_posix(),
        "bytes": out.stat().st_size,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hwp_path", type=Path, help="Source .hwp path")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output .hwpx (default: data/btrack/hwpx_poc/inbox/<stem>.hwpx)",
    )
    ap.add_argument("--meta-json", type=Path, default=None)
    args = ap.parse_args()

    src = args.hwp_path.resolve()
    out = args.out or (DEFAULT_OUT_DIR / f"{src.stem}.hwpx")
    out = out.resolve()

    info = convert_hwp_to_hwpx(src, out)
    meta = {
        "schema": "convert_hwp_to_hwpx_hancom_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "boundary_ack": "research_only",
        **info,
    }
    if args.meta_json:
        args.meta_json.parent.mkdir(parents=True, exist_ok=True)
        args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
