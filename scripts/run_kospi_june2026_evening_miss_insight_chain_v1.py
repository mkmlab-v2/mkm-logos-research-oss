#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evening miss insight chain: decomposition · flow probe · optional LLM reflect [HYPO].

Triggered on FAIL (default) or NEUTRAL_DRAW (--include-neutral-draw) for --as-of-kst session.
B-track research_only · send_gate HOLD · NOT Track A / live trading.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_calendar_miss_decomposition_v1 import (  # noqa: E402
    build_miss_decomposition,
)
from scripts.build_kospi_june2026_daily_miss_insight_v1 import (  # noqa: E402
    build_daily_miss_insight,
)

DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_FOUR_AI = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
DEFAULT_MISS_DECOMP = ROOT / "reports/kospi_june2026_calendar_miss_decomposition_v1_latest.json"
DEFAULT_MISS_PROBE = ROOT / "reports/kospi_june2026_calendar_miss_flow_probe_v1_latest.json"
DEFAULT_INSIGHT = ROOT / "reports/kospi_june2026_daily_miss_insight_v1_latest.json"
DEFAULT_CHAIN_REPORT = ROOT / "reports/kospi_june2026_evening_miss_insight_chain_v1_latest.json"

SYSTEM_PROMPT = """You are MKM B-track prophecy miss analyst (research_only).
Respond with JSON only:
{
  "reflection_ko": "2-4 sentences in Korean; factual; no buy/sell advice",
  "lens_gaps": ["short bullet strings"],
  "coordinator_lessons": ["short bullet strings"],
  "send_gate": "HOLD"
}
Do not imply live trading or Track A promotion."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_row(eval_doc: dict[str, Any], session_date: str) -> dict[str, Any] | None:
    for r in eval_doc.get("rows") or []:
        if isinstance(r, dict) and str(r.get("session_date") or "") == session_date:
            return r
    return None


def _should_trigger(row: dict[str, Any] | None, *, include_neutral: bool) -> tuple[bool, str]:
    if not row:
        return False, "no_eval_row"
    outcome = str(row.get("outcome") or "")
    if outcome == "FAIL":
        return True, outcome
    if include_neutral and outcome == "NEUTRAL_DRAW":
        return True, outcome
    return False, outcome or "unknown"


def _llm_reflect(insight: dict[str, Any], *, billing: str, timeout_sec: int) -> dict[str, Any]:
    from scripts.news_neutralizer_llm_v1 import llm_json, load_workspace_dotenv

    load_workspace_dotenv()
    compact = {
        "session_date": insight.get("session_date"),
        "outcome": insight.get("outcome"),
        "score": insight.get("score"),
        "structured_lessons": insight.get("structured_lessons"),
        "multilens": {
            "votes": (insight.get("multilens") or {}).get("votes"),
            "suppressed_bear_channels": (insight.get("multilens") or {}).get("suppressed_bear_channels"),
        },
        "four_ai": {
            "four_ai_direction": (insight.get("four_ai") or {}).get("four_ai_direction"),
            "coordinator": (insight.get("four_ai") or {}).get("coordinator"),
        },
    }
    user = json.dumps({"miss_insight": compact}, ensure_ascii=False)
    parsed, raw, resolved, model_label = llm_json(
        billing=billing,
        system=SYSTEM_PROMPT,
        user=user,
        timeout=timeout_sec,
        flash_model=os.environ.get("MKM_KOSPI_MISS_GEMINI_MODEL", "gemini-2.5-flash"),
        pro_model=os.environ.get("MKM_KOSPI_MISS_GEMINI_MODEL", "gemini-2.5-flash"),
        azure_deployment=(
            os.environ.get("MKM_KOSPI_MISS_AZURE_DEPLOYMENT")
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        ),
    )
    if not isinstance(parsed, dict):
        parsed = {"reflection_ko": (raw or "")[:800], "send_gate": "HOLD", "parse_fallback": True}
    parsed.setdefault("send_gate", "HOLD")
    parsed["billing_resolved"] = resolved
    parsed["model_label"] = model_label
    return parsed


def run_chain(
    *,
    as_of_kst: str,
    calendar_path: Path,
    eval_path: Path,
    four_ai_path: Path,
    miss_decomp_path: Path,
    miss_probe_path: Path,
    insight_path: Path,
    include_neutral_draw: bool,
    skip_flow_probe: bool,
    skip_llm: bool,
    billing: str,
    timeout_sec: int,
) -> dict[str, Any]:
    eval_doc = _load(eval_path)
    row = _eval_row(eval_doc, as_of_kst)
    trigger, reason = _should_trigger(row, include_neutral=include_neutral_draw)

    report: dict[str, Any] = {
        "schema": "kospi_june2026_evening_miss_insight_chain_v1",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "generated_at_utc": _utc_now(),
        "as_of_kst": as_of_kst,
        "triggered": trigger,
        "trigger_reason": reason,
        "steps": [],
    }

    if not trigger:
        report["skipped"] = True
        return report

    miss_doc = build_miss_decomposition(eval_doc, eval_path=eval_path)
    miss_decomp_path.parent.mkdir(parents=True, exist_ok=True)
    miss_decomp_path.write_text(json.dumps(miss_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["steps"].append({"name": "calendar_miss_decomposition", "ok": True, "miss_days": miss_doc["miss_day_count"]})

    insight = build_daily_miss_insight(
        session_date=as_of_kst,
        calendar=_load(calendar_path),
        eval_doc=eval_doc,
        four_ai=_load(four_ai_path),
    )
    if insight:
        insight_path.parent.mkdir(parents=True, exist_ok=True)
        insight_path.write_text(json.dumps(insight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["steps"].append({"name": "daily_miss_insight", "ok": True, "outcome": insight.get("outcome")})
    else:
        report["steps"].append({"name": "daily_miss_insight", "ok": False, "error": "build_returned_none"})

    if not skip_flow_probe and miss_doc.get("miss_days"):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_kospi_prophecy_miss_flow_probe_v1.py"),
                "--miss-json",
                str(miss_decomp_path),
                "--output",
                str(miss_probe_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        report["steps"].append(
            {
                "name": "miss_flow_probe",
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "tail": (proc.stdout or proc.stderr or "")[-400:],
            }
        )
    else:
        report["steps"].append({"name": "miss_flow_probe", "skipped": True})

    if not skip_llm and insight and insight.get("llm_reflect_eligible"):
        try:
            reflect = _llm_reflect(insight, billing=billing, timeout_sec=timeout_sec)
            insight["llm_reflect"] = reflect
            insight_path.write_text(json.dumps(insight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report["steps"].append(
                {
                    "name": "llm_reflect",
                    "ok": True,
                    "billing_resolved": reflect.get("billing_resolved"),
                    "model_label": reflect.get("model_label"),
                }
            )
            report["reflection_ko"] = reflect.get("reflection_ko")
        except Exception as e:
            report["steps"].append({"name": "llm_reflect", "ok": False, "error": str(e)})
    else:
        report["steps"].append({"name": "llm_reflect", "skipped": True, "skip_llm": skip_llm})

    shock_proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_kospi_hero_shock_gate_shadow_v1.py"),
            "--as-of-kst",
            as_of_kst,
            "--append-log",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    report["steps"].append(
        {
            "name": "hero_shock_gate_shadow",
            "ok": shock_proc.returncode == 0,
            "exit_code": shock_proc.returncode,
            "tail": (shock_proc.stdout or shock_proc.stderr or "")[-400:],
        }
    )

    report["artifacts"] = {
        "miss_decomposition": str(miss_decomp_path.relative_to(ROOT)).replace("\\", "/"),
        "miss_flow_probe": str(miss_probe_path.relative_to(ROOT)).replace("\\", "/"),
        "daily_miss_insight": str(insight_path.relative_to(ROOT)).replace("\\", "/"),
        "hero_shock_gate_shadow": "reports/kospi_hero_shock_gate_shadow_v1_latest.json",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of-kst", required=True)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--four-ai-json", type=Path, default=DEFAULT_FOUR_AI)
    ap.add_argument("--miss-decomp-out", type=Path, default=DEFAULT_MISS_DECOMP)
    ap.add_argument("--miss-probe-out", type=Path, default=DEFAULT_MISS_PROBE)
    ap.add_argument("--insight-out", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--report", type=Path, default=DEFAULT_CHAIN_REPORT)
    ap.add_argument("--include-neutral-draw", action="store_true")
    ap.add_argument("--skip-flow-probe", action="store_true")
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument(
        "--billing",
        choices=["auto", "azure", "developer"],
        default=os.environ.get("MKM_KOSPI_MISS_BILLING", "auto"),
    )
    ap.add_argument("--timeout-sec", type=int, default=int(os.environ.get("MKM_KOSPI_MISS_LLM_TIMEOUT_SEC", "90")))
    args = ap.parse_args(argv)

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    report = run_chain(
        as_of_kst=args.as_of_kst.strip()[:10],
        calendar_path=_p(args.calendar_json),
        eval_path=_p(args.eval_json),
        four_ai_path=_p(args.four_ai_json),
        miss_decomp_path=_p(args.miss_decomp_out),
        miss_probe_path=_p(args.miss_probe_out),
        insight_path=_p(args.insight_out),
        include_neutral_draw=args.include_neutral_draw,
        skip_flow_probe=args.skip_flow_probe,
        skip_llm=args.skip_llm,
        billing=args.billing,
        timeout_sec=args.timeout_sec,
    )

    out = _p(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "triggered": report.get("triggered"),
                "trigger_reason": report.get("trigger_reason"),
                "report": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
