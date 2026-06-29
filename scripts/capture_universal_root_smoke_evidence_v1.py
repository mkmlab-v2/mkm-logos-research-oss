#!/usr/bin/env python3
"""Capture Universal Root smoke terminal evidence for X post 2 attachment."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "exports/mkm-universal-root-v1"
SMOKE = EXPORT / "scripts/run_universal_root_oss_cursor_smoke_v1.py"
OUT_TXT = ROOT / "reports/human_paste/universal_root_smoke_terminal_evidence.txt"
OUT_PNG = ROOT / "reports/human_paste/universal_root_smoke_terminal_evidence.png"
OUT_JSON = ROOT / "reports/universal_root_smoke_evidence_capture_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _render_png(text: str, path: Path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    lines = text.splitlines() or [""]
    line_h = 18
    pad = 16
    width = min(max(len(line) for line in lines) * 9 + pad * 2, 1400)
    height = len(lines) * line_h + pad * 2
    img = Image.new("RGB", (width, height), color=(12, 12, 12))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("consola.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    y = pad
    for line in lines:
        draw.text((pad, y), line, fill=(220, 220, 220), font=font)
        y += line_h
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return True


def main() -> int:
    if not SMOKE.is_file():
        print(json.dumps({"ok": False, "error": "smoke_script_missing", "path": str(SMOKE)}))
        return 1

    proc = subprocess.run(
        [sys.executable, str(SMOKE)],
        cwd=str(EXPORT),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    combined = "\n".join(x for x in (stdout, stderr) if x)

    block = "\n".join(
        [
            "PS C:\\workspace\\mkm-universal-root> py scripts/run_universal_root_oss_cursor_smoke_v1.py",
            combined or "(no stdout)",
            f"# exit code: {proc.returncode}",
        ]
    )
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text(block + "\n", encoding="utf-8")
    png_ok = _render_png(block, OUT_PNG)

    doc = {
        "schema": "universal_root_smoke_evidence_capture_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "smoke_exit_code": proc.returncode,
        "smoke_ok": proc.returncode == 0,
        "export_cwd": str(EXPORT),
        "artifacts": {
            "txt": str(OUT_TXT.relative_to(ROOT)).replace("\\", "/"),
            "png": str(OUT_PNG.relative_to(ROOT)).replace("\\", "/") if png_ok else None,
        },
        "reproduce": "py scripts/capture_universal_root_smoke_evidence_v1.py",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": proc.returncode == 0, "png": png_ok, "out": str(OUT_JSON)}, ensure_ascii=False))
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
