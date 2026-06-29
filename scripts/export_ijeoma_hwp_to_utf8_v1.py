#!/usr/bin/env python3
"""Export IJEOMA e_drive_mirror HWP files to UTF-8 text via Hancom COM (Windows)."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = ROOT / "data/corpus/ijeoma/e_drive_mirror"
OUT_REPORT = ROOT / "data/corpus/ijeoma/_inventory/hwp_com_export_report.json"
OUT_DIR = ROOT / "data/corpus/ijeoma/originals/hwp_utf8_export_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _kill_hwp() -> None:
    subprocess.run(
        ["taskkill", "/F", "/IM", "Hwp.exe"],
        capture_output=True,
        check=False,
    )
    time.sleep(1.5)


def _export_one(hwp_path: Path, txt_path: Path, *, visible: bool = False) -> dict:
    try:
        import win32com.client  # noqa: PLC0415
    except ImportError as exc:
        return {"status": "failed", "error": "pywin32_missing", "detail": str(exc)}

    if not hwp_path.is_file():
        return {"status": "failed", "error": "missing_hwp"}

    txt_path.parent.mkdir(parents=True, exist_ok=True)
    if txt_path.exists():
        txt_path.unlink()

    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
        hwp.SetMessageBoxMode(0x00000000)
        hwp.XHwpWindows.Item(0).Visible = visible

        hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)
        hwp.HParameterSet.HFileOpenSave.filename = str(hwp_path.resolve())
        hwp.HParameterSet.HFileOpenSave.Format = "HWP"
        hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpenSave.HSet)

        text = hwp.GetTextFile("TEXT", "")
        hwp.Quit()
    except Exception as exc:
        _kill_hwp()
        return {"status": "failed", "error": "com_error", "detail": str(exc)}
    finally:
        _kill_hwp()

    min_chars = 10 if "일러두기" in hwp_path.name else 50
    if not text or len(text.strip()) < min_chars:
        return {"status": "failed", "error": "txt_too_short", "chars": len(text or "")}

    txt_path.write_text(text, encoding="utf-8")
    return {"status": "ok", "chars": len(text), "encoding_guess": "utf-8"}


def _discover_hwps(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.hwp") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=OUT_REPORT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()

    rows: list[dict] = []
    for hwp in _discover_hwps(args.root):
        rel = hwp.relative_to(args.root)
        stem = rel.as_posix().replace("/", "__")
        txt_mirror = hwp.with_suffix(".txt")
        txt_corpus = args.out_dir / f"{stem}.txt"
        row = {
            "hwp": str(hwp),
            "txt_mirror": str(txt_mirror),
            "txt_corpus": str(txt_corpus),
        }
        if args.dry_run:
            row.update({"status": "dry_run", "note": "would_export"})
        else:
            result = _export_one(hwp, txt_corpus, visible=args.visible)
            if result.get("status") != "ok":
                time.sleep(2)
                retry = _export_one(hwp, txt_corpus, visible=args.visible)
                if retry.get("status") == "ok":
                    retry["retried"] = True
                    result = retry
            row.update(result)
            if result.get("status") == "ok":
                txt_corpus.parent.mkdir(parents=True, exist_ok=True)
                txt_mirror.write_text(txt_corpus.read_text(encoding="utf-8"), encoding="utf-8")
        rows.append(row)
        print(json.dumps({"hwp": hwp.name, **{k: row[k] for k in row if k in ("status", "chars", "error")}}, ensure_ascii=False))

    counts = {
        "total": len(rows),
        "ok": sum(1 for r in rows if r.get("status") == "ok"),
        "failed": sum(1 for r in rows if r.get("status") == "failed"),
        "skipped": sum(1 for r in rows if r.get("status") == "skipped"),
        "dry_run": sum(1 for r in rows if r.get("status") == "dry_run"),
    }
    doc = {
        "schema": "hwp_com_export_report_v1",
        "generated_at_utc": _utc(),
        "root": str(args.root),
        "out_dir": str(args.out_dir),
        "rows": rows,
        "counts": counts,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    merge_manifest = args.out_dir / "IJEOMA_HWP_UTF8_MANIFEST_v1.json"
    merge_manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "counts": counts}, ensure_ascii=False))
    return 0 if counts["failed"] == 0 and counts["ok"] + counts["dry_run"] == counts["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
