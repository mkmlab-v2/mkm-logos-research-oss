#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-date lens shadow chain: extend JSONL → shadow calendar → AB → eval [HYPO].

Does NOT overwrite published active calendar or apply weights.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_per_date_lens_shadow_chain_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "optional": optional,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-500:],
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", required=True)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--through-date", default=None, help="JSONL extend target (default month-end or as-of)")
    ap.add_argument("--skip-jsonl-extend", action="store_true")
    ap.add_argument("--skip-panel-rebuild", action="store_true", default=True)
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    ym = ns.year_month.strip()
    tag = ym.replace("-", "")
    as_of = ns.as_of_kst
    if not as_of:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

        as_of = last_krx_trading_day_on_or_before(date.today()) or date.today().isoformat()
    through = ns.through_date or as_of
    published = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    if ym == "2026-06":
        published = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    shadow = ROOT / f"reports/kospi_{tag}_per_date_lens_shadow_calendar_v1.json"
    shadow_eval = ROOT / f"reports/kospi_{tag}_per_date_lens_shadow_eval_latest.json"
    if ym == "2026-06":
        shadow_eval = ROOT / "reports/kospi_june2026_per_date_lens_shadow_eval_latest.json"

    steps: list[dict[str, Any]] = []
    if not ns.skip_jsonl_extend:
        steps.append(
            _run(
                "1_extend_manseryeok_jsonl",
                [
                    PY,
                    "scripts/extend_manseryeok_session_jsonl_v1.py",
                    "--through-date",
                    through,
                ],
            )
        )
    cal_cmd = [
        PY,
        "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py",
        "--year-month",
        ym,
        "--lens-mode",
        "per_date",
        "--profile",
        "v2_multilens",
    ]
    if ns.skip_panel_rebuild:
        cal_cmd.append("--skip-panel-rebuild")
    steps.append(_run("2_build_per_date_shadow_calendar", cal_cmd))
    steps.append(
        _run(
            "3_static_vs_per_date_ab",
            [
                PY,
                "scripts/build_kospi_june2026_static_vs_per_date_lens_ab_v1.py",
                "--calendar-json",
                str(published),
            ],
        )
    )
    steps.append(
        _run(
            "4_eval_shadow_calendar",
            [
                PY,
                "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
                "--calendar-json",
                str(shadow),
                "--output",
                str(shadow_eval),
                "--as-of-kst",
                as_of,
            ],
        )
    )
    steps.append(
        _run(
            "5_restore_published_eval",
            [
                PY,
                "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
                "--calendar-json",
                str(published),
                "--as-of-kst",
                as_of,
            ],
            optional=True,
        )
    )

    required_fail = [s for s in steps if not s.get("optional") and s["exit_code"] != 0]
    ab = _read_json(ROOT / "reports/kospi_june2026_static_vs_per_date_lens_ab_v1_latest.json")
    sf = ab.get("scored_forward_ab") if isinstance(ab.get("scored_forward_ab"), dict) else {}
    shadow_eval_doc = _read_json(shadow_eval)
    doc = {
        "schema": "kospi_per_date_lens_shadow_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "production_apply_authorized": False,
        "year_month": ym,
        "as_of_kst": as_of,
        "through_date": through,
        "quality_ok": len(required_fail) == 0,
        "steps": steps,
        "artifacts": {
            "published_calendar": str(published).replace("\\", "/"),
            "shadow_calendar": str(shadow).replace("\\", "/"),
            "shadow_eval": str(shadow_eval).replace("\\", "/"),
            "static_vs_per_date_ab": "reports/kospi_june2026_static_vs_per_date_lens_ab_v1_latest.json",
        },
        "ab_summary": {
            "n_scored": sf.get("n_scored"),
            "published_soft_hit_rate": sf.get("published_soft_hit_rate"),
            "static_replay_soft_hit_rate": sf.get("static_replay_soft_hit_rate"),
            "per_date_replay_soft_hit_rate": sf.get("per_date_replay_soft_hit_rate"),
            "delta_per_date_minus_static_soft": sf.get("delta_per_date_minus_static_soft"),
        },
        "shadow_eval_summary": {
            "n_scored": shadow_eval_doc.get("n_scored"),
            "soft_hit_rate": (shadow_eval_doc.get("metrics") or {}).get("soft_hit_rate"),
        },
        "reproduce": f"py scripts/run_kospi_per_date_lens_shadow_chain_v1.py --year-month {ym}",
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_per_date_lens_shadow_chain_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["quality_ok"],
                "shadow_calendar": str(shadow),
                "per_date_soft": sf.get("per_date_replay_soft_hit_rate"),
                "shadow_eval_soft": (shadow_eval_doc.get("metrics") or {}).get("soft_hit_rate"),
            },
            ensure_ascii=False,
        )
    )
    return 1 if required_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
