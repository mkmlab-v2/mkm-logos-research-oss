#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily prophecy evolution: dual_path_v2 predict · evening score · weekend prep [HYPO].

Morning (거래일): 캘린더 seal + v2 예측 카드
Evening: OHLCV·채점·shadow·FAIL 통찰·예측 카드(정답)
Weekend: macro/입력 갱신 + 다음 거래일 prep 카드 (KOSPI 방향 채점 없음)

research_only · active calendar 미변경 · send_gate HOLD
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
OUT = ROOT / "reports/kospi_daily_prophecy_evolution_loop_v1_latest.json"
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
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-400:],
    }


def _last_krx_session() -> str:
    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    return last_krx_trading_day_on_or_before(date.today()) or date.today().isoformat()


def _is_trading_today() -> bool:
    from scripts.kospi_krx_calendar_v1 import krx_trading_days

    today = date.today().isoformat()
    return today in krx_trading_days(date.today(), date.today())


def _build_checkpoint_message(*, phase: str, as_of: str, ym: str) -> str | None:
    card_path = ROOT / "reports/kospi_daily_dual_path_prophecy_latest.json"
    if not card_path.is_file():
        return None
    card = json.loads(card_path.read_text(encoding="utf-8-sig"))
    sess = str(card.get("session_date") or as_of)
    pred = card.get("predicted_direction") or "?"
    oc = card.get("predicted_outcome") or "pending"
    route = card.get("dual_path_v2_route") or "baseline"
    if phase == "evening":
        return (
            f"KOSPI v2 shadow {sess} {pred} {oc} route={route} · ym={ym} evening_score [HYPO research_only]"
        )
    if phase == "weekend":
        return f"KOSPI v2 weekend prep {sess} pred={pred} route={route} · ym={ym} [HYPO]"
    if phase == "morning":
        return f"KOSPI v2 morning pred {sess} {pred} route={route} · ym={ym} [HYPO]"
    return None


def _run_checkpoint(message: str) -> dict[str, Any]:
    proc = subprocess.run(
        [PY, "scripts/athena_checkpoint.py", message],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "name": "athena_checkpoint",
        "cmd": [PY, "scripts/athena_checkpoint.py", message],
        "exit_code": proc.returncode,
        "optional": True,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", choices=("morning", "evening", "weekend", "all"), default="evening")
    ap.add_argument("--year-month", default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--skip-heavy", action="store_true")
    ap.add_argument("--skip-checkpoint", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    as_of = ns.as_of_kst or _last_krx_session()
    ym = ns.year_month or as_of[:7]
    tag = ym.replace("-", "")
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    if ym == "2026-06" and not cal.is_file():
        cal = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"

    steps: list[dict[str, Any]] = []

    def step(name: str, cmd: list[str], *, optional: bool = False) -> None:
        steps.append(_run(name, cmd, optional=optional))

    if ns.phase in ("morning", "all"):
        step(
            "morning_premarket_news_overnight_ingest",
            [
                PY,
                "scripts/run_kospi_premarket_news_overnight_ingest_chain_v1.py",
                "--allow-naver-cache-fallback",
            ],
            optional=True,
        )
        step(
            "morning_calendar_seal",
            [
                PY,
                "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py",
                "--year-month",
                ym,
                "--skip-panel-rebuild",
                "--profile",
                "v2_multilens",
                "--seal-date",
                date.today().isoformat(),
            ],
        )
        step(
            "morning_dual_path_shadow",
            [
                PY,
                "scripts/build_kospi_dual_path_conflict_shadow_v1.py",
                "--year-month",
                ym,
                "--as-of-kst",
                as_of,
            ],
        )
        mode = "today_trading" if _is_trading_today() else "next_session_prep"
        step(
            "morning_emit_prophecy_card",
            [
                PY,
                "scripts/emit_kospi_daily_dual_path_prophecy_v1.py",
                "--data-mode",
                mode,
            ],
        )
        step(
            "morning_briefing_advisory",
            [PY, "scripts/run_kospi_evening_briefing_chain_v1.py", "--session-date", as_of],
            optional=True,
        )

    if ns.phase in ("evening", "all"):
        step(
            "evening_observation_loop",
            [
                PY,
                "scripts/run_kospi_daily_observation_loop_v1.py",
                "--year-month",
                ym,
                "--as-of-kst",
                as_of,
                "--phase",
                "evening",
            ],
        )
        if not ns.skip_heavy:
            step(
                "evening_miss_insight",
                [
                    PY,
                    "scripts/run_kospi_june2026_evening_miss_insight_chain_v1.py",
                    "--as-of-kst",
                    as_of,
                    "--calendar-json",
                    str(cal),
                    "--skip-llm",
                ],
                optional=True,
            )
        step(
            "evening_dual_path_shadow",
            [
                PY,
                "scripts/build_kospi_dual_path_conflict_shadow_v1.py",
                "--year-month",
                ym,
                "--as-of-kst",
                as_of,
            ],
        )
        step(
            "evening_emit_scored_card",
            [
                PY,
                "scripts/emit_kospi_daily_dual_path_prophecy_v1.py",
                "--session-date",
                as_of,
                "--data-mode",
                "evening_score",
            ],
        )

    if ns.phase in ("weekend", "all"):
        step(
            "weekend_premarket_news_overnight_ingest",
            [
                PY,
                "scripts/run_kospi_premarket_news_overnight_ingest_chain_v1.py",
                "--allow-naver-cache-fallback",
            ],
            optional=True,
        )
        macro_poc = ROOT / "scripts/build_kospi_june2026_macro_daily_refresh_poc_v1.py"
        if macro_poc.is_file():
            step(
                "weekend_macro_refresh_poc",
                [PY, str(macro_poc), "--year-month", ym],
                optional=True,
            )
        step(
            "weekend_dual_path_shadow",
            [
                PY,
                "scripts/build_kospi_dual_path_conflict_shadow_v1.py",
                "--year-month",
                ym,
                "--as-of-kst",
                as_of,
            ],
            optional=True,
        )
        step(
            "weekend_next_session_prep",
            [
                PY,
                "scripts/emit_kospi_daily_dual_path_prophecy_v1.py",
                "--data-mode",
                "next_session_prep",
            ],
            optional=True,
        )

    required_fail = [s for s in steps if not s.get("optional") and s["exit_code"] != 0]
    quality_ok = len(required_fail) == 0
    if quality_ok and not ns.skip_checkpoint and ns.phase in ("morning", "evening", "weekend", "all"):
        msg = _build_checkpoint_message(phase=ns.phase, as_of=as_of, ym=ym)
        if msg:
            steps.append(_run_checkpoint(msg))

    doc = {
        "schema": "kospi_daily_prophecy_evolution_loop_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "scoring_arm_fixed": "dual_path_v2_router",
        "phase": ns.phase,
        "year_month": ym,
        "as_of_kst": as_of,
        "quality_ok": quality_ok,
        "steps": steps,
        "artifacts": {
            "daily_prophecy_card": "reports/kospi_daily_dual_path_prophecy_latest.json",
            "daily_prophecy_log": "reports/kospi_daily_dual_path_prophecy_log_v1.jsonl",
            "dual_path_shadow": "reports/kospi_dual_path_conflict_shadow_v1_latest.json",
            "observation_loop": "reports/kospi_daily_observation_loop_v1_latest.json",
        },
        "reproduce": f"py scripts/run_kospi_daily_prophecy_evolution_loop_v1.py --phase {ns.phase} --year-month {ym}",
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_daily_prophecy_evolution_loop_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["quality_ok"], "phase": ns.phase, "as_of": as_of}, ensure_ascii=False))
    return 1 if required_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
