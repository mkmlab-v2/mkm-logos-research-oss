#!/usr/bin/env python3
"""Cross-check Han Vocology appendix CB dashboards vs pilot JSONL (legacy + pilot cohorts)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
APPENDIX = ROOT / "docs/research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md"
OUT = ROOT / "docs/final/artifacts/han_vocology_cb_dashboard_pilot_crosscheck_v1_latest.json"

TRACKED_CB = (
    "CB-06-A",
    "CB-06-B",
    "CB-08-A",
    "CB-08-B",
    "CB-09-A",
    "CB-09-B",
    "CB-10-A",
    "CB-10-B",
    "CB-11",
    "CB-12",
    "CB-13",
    "CB-14",
    "CB-15",
    "CB-16",
)

CB_STYLE: dict[str, str] = {
    "CB-06-A": "fep",
    "CB-06-B": "p4",
    "CB-08-A": "f_sum",
    "CB-08-B": "fep",
    "CB-09-A": "fep",
    "CB-09-B": "fep",
    "CB-10-A": "fep",
    "CB-10-B": "fep",
    "CB-11": "fep",
    "CB-12": "fep",
    "CB-13": "p4",
    "CB-14": "fep",
    "CB-15": "fep",
    "CB-16": "fep",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _subtotals(scores: dict[str, int]) -> tuple[int, int, int]:
    f = sum(v for k, v in scores.items() if k.startswith("F"))
    e = sum(v for k, v in scores.items() if k.startswith("E"))
    p = sum(v for k, v in scores.items() if k.startswith("P"))
    return f, e, p


def _delta_pattern(delta: float | int | None) -> str:
    if delta is None:
        return "—"
    compact = f"{float(delta):g}"
    if compact.isdigit():
        return rf"(?:{re.escape(compact)}(?:\.0)?)"
    return re.escape(compact)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _section_slice(text: str, cb_id: str) -> str:
    pattern = rf"### {re.escape(cb_id)}.*?(?=### |\Z)"
    m = re.search(pattern, text, flags=re.S)
    return m.group(0) if m else ""


def _check_fep_row(section: str, week: int, total: int, f: int, e: int, p: int, delta: float | int | None) -> bool:
    if delta is None:
        pat = rf"\|\s*{week}\s*\|\s*{total}\s*\|\s*—\s*\|\s*{f}\s*\|\s*{e}\s*\|\s*{p}\s*\|"
    else:
        delta_pat = _delta_pattern(delta)
        pat = rf"\|\s*{week}\s*\|\s*{total}\s*\|\s*{delta_pat}%?\s*\|\s*{f}\s*\|\s*{e}\s*\|\s*{p}\s*\|"
    return re.search(pat, section) is not None


def _check_p4_row(section: str, week: int, total: int, p4: int) -> bool:
    pat = rf"\|\s*{week}\s*\|\s*{total}\s*\|[^|]+\|\s*{p4}\s*\|"
    return re.search(pat, section) is not None


def _check_f_sum_row(section: str, week: int, total: int, f: int) -> bool:
    pat = rf"\|\s*{week}\s*\|\s*{total}\s*\|[^|]+\|\s*{f}\s*\|"
    return re.search(pat, section) is not None


def main() -> int:
    if not JSONL.is_file() or not APPENDIX.is_file():
        print(json.dumps({"ok": False, "error": "missing_input"}, ensure_ascii=False))
        return 1

    appendix = APPENDIX.read_text(encoding="utf-8")
    rows = _load_jsonl(JSONL)
    checks: list[dict[str, Any]] = []
    cohort_rows: list[dict[str, Any]] = []

    for cb_id in TRACKED_CB:
        style = CB_STYLE[cb_id]
        section = _section_slice(appendix, cb_id)
        checks.append({"name": f"appendix_section_{cb_id}", "ok": bool(section)})

        cb_records = sorted(
            [r for r in rows if r.get("cb_id") == cb_id],
            key=lambda r: int(r.get("visit_week") or 0),
        )
        for rec in cb_records:
            week = int(rec["visit_week"])
            total = int(rec["total"])
            f, e, p = _subtotals(rec["scores"])
            delta = rec.get("delta_pct_vs_week0")
            row_spec = {
                "cb_id": cb_id,
                "visit_week": week,
                "total": total,
                "F": f,
                "E": e,
                "P": p,
                "delta_pct_vs_week0": delta,
                "pseudonym_id": rec.get("pseudonym_id"),
            }
            cohort_rows.append(row_spec)

            row_pat = rf"\|\s*{week}\s*\|\s*{total}\s*\|"
            checks.append({"name": f"{cb_id}_w{week}_total_in_appendix", "ok": re.search(row_pat, section) is not None})

            if style == "fep":
                checks.append(
                    {
                        "name": f"{cb_id}_w{week}_fep_delta_in_appendix",
                        "ok": _check_fep_row(section, week, total, f, e, p, delta),
                    }
                )
            elif style == "p4":
                p4 = rec["scores"].get("P4")
                checks.append(
                    {"name": f"{cb_id}_w{week}_p4_in_appendix", "ok": _check_p4_row(section, week, total, int(p4))}
                )
            elif style == "f_sum":
                checks.append(
                    {"name": f"{cb_id}_w{week}_f_sum_in_appendix", "ok": _check_f_sum_row(section, week, total, f)}
                )

        if cb_id == "CB-06-A":
            has_w2 = re.search(r"\|\s*2\s*\|\s*30\s*\|", section) is not None
            checks.append({"name": "CB-06-A_no_pilot_missing_week2_row", "ok": not has_w2})

    ok = all(c["ok"] for c in checks)
    report = {
        "schema": "han_vocology_cb_dashboard_pilot_crosscheck_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "tracked_cb": list(TRACKED_CB),
        "pilot_jsonl": str(JSONL.relative_to(ROOT)).replace("\\", "/"),
        "appendix": str(APPENDIX.relative_to(ROOT)).replace("\\", "/"),
        "cohort_rows": cohort_rows,
        "checks": checks,
        "reproducible_command": "py scripts/check_han_vocology_appendix_cb_dashboard_vs_pilot_v1.py",
        "boundary_ack": "[HYPO] education dashboards aligned to pilot JSONL where tracked",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = sum(1 for c in checks if c["ok"])
    print(json.dumps({"ok": ok, "checks_pass": passed, "checks_total": len(checks), "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
