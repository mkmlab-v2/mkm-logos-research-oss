#!/usr/bin/env python3
"""OI 20460237 — full submission doc chain: 과제소개서 발췌 → 사업계획서 HWP/PDF → 제출패키지."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "data/btrack/hwpx_poc/inbox/open_innovation_20460237_official_v1.hwpx"
SLOTS = ROOT / "data/btrack/hwpx_poc/slots_open_innovation_20460237_v1.json"
FILLED_HWPX = ROOT / "reports/kstartup_open_innovation_20460237_filled_v4.hwpx"
FILLED_HWP = ROOT / "reports/kstartup_open_innovation_20460237_filled_v4.hwp"
FILLED_PDF = ROOT / "reports/kstartup_open_innovation_20460237_filled_v4.pdf"
FILL_REPORT = ROOT / "reports/kstartup_open_innovation_20460237_hwpx_fill_latest.json"
META_OUT = ROOT / "reports/kstartup_open_innovation_20460237_submission_complete_latest.json"
DEMAND_PDF = Path.home() / "Downloads" / "(별첨1) 수요기업 과제소개서.pdf"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_template(explicit: Path | None) -> Path:
    if explicit and explicit.is_file():
        return explicit.resolve()
    downloads = Path.home() / "Downloads"
    candidates = sorted(
        downloads.glob("*오픈이노베이션*모집공고*.hwpx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("HWPX template not found in Downloads")
    return candidates[0].resolve()


def _run(cmd: list[str]) -> None:
    print(">>", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template-hwpx", type=Path, default=None)
    ap.add_argument("--demand-pdf", type=Path, default=DEMAND_PDF)
    ap.add_argument("--skip-hancom", action="store_true")
    ap.add_argument("--skip-pdf", action="store_true")
    args = ap.parse_args()

    template = _find_template(args.template_hwpx)
    INBOX.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, INBOX)

    _run(
        [
            sys.executable,
            "scripts/extract_kstartup_oi_demand_task_intro_v1.py",
            "--pdf",
            str(args.demand_pdf.resolve()),
        ]
    )
    _run([sys.executable, "scripts/build_kstartup_open_innovation_20460237_hwpx_slots_v1.py"])
    _run(
        [
            sys.executable,
            "scripts/fill_hwpx_by_label_cells_v1.py",
            "--hwpx",
            str(INBOX),
            "--slots-json",
            str(SLOTS),
            "--out",
            str(FILLED_HWPX),
            "--report-json",
            str(FILL_REPORT),
        ]
    )

    hwp_ok = False
    pdf_ok = False
    if not args.skip_hancom:
        try:
            _run(
                [
                    sys.executable,
                    "scripts/resave_hwpx_via_hancom_v1.py",
                    "--hwpx",
                    str(FILLED_HWPX),
                    "--out-hwp",
                    str(FILLED_HWP),
                ]
            )
            hwp_ok = FILLED_HWP.is_file()
        except subprocess.CalledProcessError:
            print("WARN: Hancom HWP resave failed", flush=True)

    if hwp_ok and not args.skip_pdf:
        import time  # noqa: PLC0415

        time.sleep(2)
        try:
            _run(
                [
                    sys.executable,
                    "scripts/export_hwp_pdf_hancom_v1.py",
                    "--hwp",
                    str(FILLED_HWP),
                    "--out-pdf",
                    str(FILLED_PDF),
                ]
            )
            pdf_ok = FILLED_PDF.is_file()
        except subprocess.CalledProcessError:
            print("WARN: Hancom PDF export failed", flush=True)

    _run(
        [
            sys.executable,
            "scripts/build_kstartup_open_innovation_20460237_submission_pack_v1.py",
            "--hwp",
            str(FILLED_HWP if hwp_ok else FILLED_HWPX),
            "--hwpx",
            str(FILLED_HWPX),
        ]
        + (["--pdf", str(FILLED_PDF)] if pdf_ok else [])
    )

    fill_report = json.loads(FILL_REPORT.read_text(encoding="utf-8")) if FILL_REPORT.is_file() else {}
    pack = json.loads(
        (ROOT / "reports/kstartup_open_innovation_20460237_submission_pack_latest.json").read_text(
            encoding="utf-8"
        )
    )

    meta = {
        "ok": pack.get("ok") and len(fill_report.get("failed") or []) == 0,
        "schema": "kstartup_open_innovation_20460237_submission_complete_v1",
        "generated_at_utc": _utc(),
        "demand_pdf": str(args.demand_pdf),
        "filled_hwpx": str(FILLED_HWPX.relative_to(ROOT)).replace("\\", "/"),
        "filled_hwp": str(FILLED_HWP.relative_to(ROOT)).replace("\\", "/") if hwp_ok else "",
        "filled_pdf": str(FILLED_PDF.relative_to(ROOT)).replace("\\", "/") if pdf_ok else "",
        "downloads_pack_dir": pack.get("downloads_pack_dir"),
        "fill_applied": len(fill_report.get("applied") or []),
        "fill_failed": len(fill_report.get("failed") or []),
        "human_verify": pack.get("human_verify"),
        "repro": "py scripts/run_kstartup_open_innovation_20460237_submission_complete_v1.py",
    }
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0 if meta["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
