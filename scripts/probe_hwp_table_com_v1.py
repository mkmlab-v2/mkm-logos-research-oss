#!/usr/bin/env python3
"""Probe Hancom HWP COM table/cell APIs (local Windows only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HWPX = ROOT / "data/btrack/hwpx_poc/inbox/ms_microsoft_ma_jung_program_business_plan_v1.hwpx"


def main() -> int:
    try:
        import win32com.client  # noqa: PLC0415
    except ImportError:
        print("win32com missing")
        return 1

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_HWPX
    if not path.is_file():
        print("missing", path)
        return 1

    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
    hwp.SetMessageBoxMode(0x00000000)
    hwp.XHwpWindows.Item(0).Visible = False

    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)
    hwp.HParameterSet.HFileOpenSave.filename = str(path.resolve())
    fmt = "HWPX" if path.suffix.lower() == ".hwpx" else "HWP"
    hwp.HParameterSet.HFileOpenSave.Format = fmt
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)

    # Scan controls
    tbl_count = 0
    try:
        hwp.InitScan(0, 0x007F)  # scan whole doc
        while True:
            ctrl = hwp.ScanGetControl()
            if ctrl is None:
                break
            cid = str(getattr(ctrl, "CtrlID", "") or "")
            if "tbl" in cid.lower() or cid in ("tbl", "wp_tbl"):
                tbl_count += 1
                if tbl_count <= 3:
                    print("table ctrl", tbl_count, "CtrlID", cid, "UserDesc", getattr(ctrl, "UserDesc", ""))
    except Exception as exc:
        print("InitScan failed", exc)

    print("table controls seen:", tbl_count)

    # Try TableCellBlock on first table via caret move
    for action in ("TableCellBlock", "TableCellBlockExtend", "MoveSelTableRight"):
        try:
            ok = hwp.HAction.Run(action)
            print("HAction.Run", action, ok)
        except Exception as exc:
            print("HAction.Run", action, "err", exc)

    hwp.Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
