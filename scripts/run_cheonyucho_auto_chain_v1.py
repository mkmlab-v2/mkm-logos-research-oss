#!/usr/bin/env python3
"""One-shot cheonyucho B-track automation chain (research_only, HOLD)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_auto_chain_run_v1.json"

STEPS: list[tuple[str, list[str]]] = [
    ("external_catalog", [sys.executable, "scripts/run_cheonyucho_external_catalog_probe_v1.py"]),
    ("thesis_appendix_sweep", [sys.executable, "scripts/run_cheonyucho_thesis_appendix_sweep_v1.py"]),
    ("opac_probe", [sys.executable, "scripts/run_cheonyucho_opac_probe_v1.py"]),
    ("t1_toc_fetch", [sys.executable, "scripts/run_ijeoma_t1_toc_fetch_v1.py"]),
    ("catalog_merge_probe", [sys.executable, "scripts/run_cheonyucho_catalog_merge_probe_v1.py"]),
    ("park1985_appendix_grep", [sys.executable, "scripts/run_cheonyucho_park1985_appendix_grep_v1.py"]),
    ("acquisition_probe", [sys.executable, "scripts/run_cheonyucho_acquisition_probe_v1.py"]),
    ("kci_pdf_probe", [sys.executable, "scripts/probe_kci_landing_pdf_v1.py"]),
    ("kci_fetch_kim2006", [sys.executable, "scripts/fetch_kci_pdf_v1.py", "--arti-id", "ART001014143", "--slug", "KIM_NAMIL_2006_HANUISAHYEJI"]),
    ("medhist_fetch_kim2006", [sys.executable, "scripts/fetch_medhist_pdf_v1.py", "--number", "2131", "--slug", "KIM_NAMIL_2006_HANUISAHYEJI"]),
    ("secondary_corpus_dr", [sys.executable, "scripts/run_cheonyucho_secondary_corpus_dr_v1.py"]),
    ("ultra_dr_belt", [sys.executable, "scripts/run_cheonyucho_ultra_dr_belt_v1.py"]),
    ("phase3_manifest", [sys.executable, "scripts/build_scispace_followup_phase3_v1.py"]),
    ("gate", [sys.executable, "scripts/check_cheonyucho_acquisition_gate_v1.py"]),
    ("g_vault_push", [sys.executable, "scripts/push_ijeoma_recent_to_g_vault_v1.py"]),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_step(name: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (proc.stdout or proc.stderr or "")[-500:]
    return {"name": name, "cmd": cmd, "exit_code": proc.returncode, "tail": tail}


def maybe_grep_kim_pdf() -> dict | None:
    for name in ("KIM_NAMIL_2006_HANUISAHYEJI_medhist.pdf", "KIM_NAMIL_2006_HANUISAHYEJI_kci.pdf"):
        pdf = ROOT / "docs/research/raw" / name
        if pdf.is_file() and pdf.stat().st_size >= 10_000:
            cmd = [
                sys.executable,
                "scripts/grep_cheonyucho_pdf_v1.py",
                "--pdf",
                str(pdf.relative_to(ROOT)),
                "--arti-id",
                "ART001014143",
                "--source-url",
                "https://www.medhist.or.kr/journal/view.php?number=2131",
                "--out",
                "reports/constitution/btrack_pilot/kim_namil_2006_pdf_grep_cheonyucho_v1.json",
            ]
            return run_step("kim2006_pdf_grep", cmd)
    return {"skipped": True, "reason": "no_valid_pdf"}


def main() -> int:
    rows = [run_step(name, cmd) for name, cmd in STEPS]
    grep_row = maybe_grep_kim_pdf()
    if grep_row:
        rows.append(grep_row)

    ok = all(
        r["exit_code"] == 0
        for r in rows
        if not r.get("skipped") and r["name"] not in ("kci_fetch_kim2006", "medhist_fetch_kim2006")
    )
    gate_tail = next((r["tail"] for r in rows if r["name"] == "gate"), "")
    doc = {
        "schema": "cheonyucho_auto_chain_run_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ok": ok,
        "steps": rows,
        "gate_tail": gate_tail,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "steps": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
