#!/usr/bin/env py
"""B-track [HYPO] — local Docling document ingress smoke (no Track A / no production claim)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data/btrack_fixtures/docling_smoke_v1.md"
OUT = ROOT / "reports/docling_btrack_smoke_v1_latest.json"
OUT_MD = ROOT / "reports/docling_btrack_smoke_v1_latest.md"
VENV_DIR = ROOT / ".venv-btrack-docling"
VENV_PY = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
WORKER_ENV = "MKM_DOCLING_BTRACK_WORKER"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _convert_with_docling(input_path: Path) -> dict[str, object]:
    from docling.document_converter import DocumentConverter  # type: ignore

    converter = DocumentConverter()
    result = converter.convert(str(input_path.resolve()))
    markdown = result.document.export_to_markdown()
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown, encoding="utf-8")
    preview = markdown.strip().replace("\n", " ")[:240]
    return {
        "status": "ok",
        "markdown_path": _rel(OUT_MD),
        "markdown_bytes": OUT_MD.stat().st_size,
        "markdown_chars": len(markdown),
        "preview": preview,
        "input_suffix": input_path.suffix.lower(),
        "runtime": "in_process",
    }


def _run_worker_subprocess(python_exe: Path, input_path: Path) -> tuple[int, dict[str, object] | None, str]:
    env = os.environ.copy()
    env[WORKER_ENV] = "1"
    proc = subprocess.run(
        [str(python_exe), str(Path(__file__).resolve()), "--input", str(input_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    raw = (proc.stdout or proc.stderr).strip()
    if not raw:
        return proc.returncode, None, "empty_worker_output"
    try:
        payload = json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        return proc.returncode, None, raw[-500:]
    return proc.returncode, payload, ""


def _fixture_only_ok(input_path: Path) -> dict[str, object]:
    text = input_path.read_text(encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")
    preview = text.strip().replace("\n", " ")[:240]
    return {
        "status": "ok_fixture_only",
        "markdown_path": _rel(OUT_MD),
        "markdown_bytes": OUT_MD.stat().st_size,
        "markdown_chars": len(text),
        "preview": preview,
        "input_suffix": input_path.suffix.lower(),
        "runtime": "fixture_copy",
        "note": "Docling unavailable; fixture copied for paste-assistant wiring only.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Local document path (md/pdf/docx); default B-track fixture",
    )
    ap.add_argument(
        "--fixture-only",
        action="store_true",
        help="Copy fixture to reports without Docling (offline wiring smoke)",
    )
    args = ap.parse_args()

    report: dict[str, object] = {
        "schema": "docling_btrack_smoke_v1",
        "lane": "b_track_hypo",
        "generated_at_utc": _utc_now(),
        "reproduce": "py scripts/smoke_docling_btrack_v1.py",
        "reproduce_venv": (
            "powershell -File scripts/Invoke-DoclingBtrackSmoke_v1.ps1 -BootstrapVenv"
        ),
        "input_path": _rel(args.input),
    }

    if not args.input.is_file():
        report.update({"status": "fail", "error": "input_missing", "detail": str(args.input)})
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    if args.fixture_only:
        report.update(_fixture_only_ok(args.input))
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if os.environ.get(WORKER_ENV) == "1":
        try:
            report.update(_convert_with_docling(args.input))
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            return 0
        except Exception as exc:  # noqa: BLE001
            report.update({"status": "fail", "error": str(exc), "runtime": "worker"})
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
            return 1

    if VENV_PY.is_file():
        code, payload, detail = _run_worker_subprocess(VENV_PY, args.input)
        if code == 0 and payload and payload.get("status") == "ok":
            report.update(payload)
            report["runtime"] = "venv_subprocess"
            report["venv_python"] = _rel(VENV_PY)
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            return 0
        if payload:
            report.update(payload)
            report["worker_detail"] = detail
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
            return 1 if payload.get("status") == "fail" else 0

    try:
        from docling.document_converter import DocumentConverter  # type: ignore  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        report.update(
            {
                "status": "skip",
                "reason": "docling_unavailable",
                "detail": str(exc)[:500],
                "hint": (
                    "powershell -File scripts/Invoke-DoclingBtrackSmoke_v1.ps1 -BootstrapVenv "
                    "or py scripts/smoke_docling_btrack_v1.py --fixture-only"
                ),
                "venv_expected": _rel(VENV_DIR),
            }
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    try:
        report.update(_convert_with_docling(args.input))
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        report.update({"status": "fail", "error": str(exc)})
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
