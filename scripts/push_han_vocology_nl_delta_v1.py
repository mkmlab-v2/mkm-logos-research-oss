#!/usr/bin/env python3
"""Push Han Vocology NL delta sources (OSCE rubric + graduation gate) via nlm CLI."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/han_vocology_nl_delta_v1_latest.json"
THEORY_URL = ROOT / "reports/notebooklm_theory_mathematization_notebook_url_v1.txt"

SOURCES: list[tuple[str, Path]] = [
    ("Han_Vocology_OSCE_Rubric_M20.md", ROOT / "reports/han_vocology_osce_rubric_nl_summary_v1_latest.md"),
    ("Han_Vocology_Graduation_Gate_M21.md", ROOT / "reports/han_vocology_graduation_gate_v1_latest.md"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_osce_summary() -> Path:
    rubric_path = ROOT / "docs/final/artifacts/han_vocology_osce_rubric_v1_latest.json"
    out = SOURCES[0][1]
    if not rubric_path.is_file():
        return out
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    stations = rubric.get("stations") or []
    lines = [
        "# 한의음성학 OSCE 루브릭 (M20)",
        "",
        "B-track · send_gate HOLD · patient-facing blocked",
        "",
        f"- stations: {len(stations)}",
        f"- pool: {rubric.get('pass_rules', {}).get('station_pool_max_points')}pt",
        f"- pass: ≥{rubric.get('pass_rules', {}).get('station_pool_min_points')}pt",
        "",
        "## Stations",
        "",
    ]
    for s in stations:
        lines.append(f"- {s.get('id')}: {s.get('cb_id')} · {s.get('task_ko')} · {s.get('policy')}")
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    from notebooklm_nlm_refresh_util_v1 import delete_by_title, notebook_id_from_url_file

    _ensure_osce_summary()
    if not THEORY_URL.is_file():
        report = {"schema": "han_vocology_nl_delta_v1", "ok": False, "reason": "theory_url_missing"}
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 1

    nb = notebook_id_from_url_file(THEORY_URL)
    pushes: list[dict[str, Any]] = []
    for title, path in SOURCES:
        if not path.is_file():
            pushes.append({"title": title, "ok": False, "reason": "file_missing"})
            continue
        delete_by_title(nb, title)
        proc = subprocess.run(
            ["nlm", "source", "add", nb, "--file", str(path), "--title", title, "--wait"],
            capture_output=True,
            text=True,
            check=False,
        )
        pushes.append(
            {
                "title": title,
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-200:],
            }
        )

    ok = all(p.get("ok") for p in pushes)
    report = {
        "schema": "han_vocology_nl_delta_v1",
        "ok": ok,
        "generated_at_utc": _utc(),
        "notebook_id": nb,
        "pushes": pushes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "pushes": len(pushes), "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
