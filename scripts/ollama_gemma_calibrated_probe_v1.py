#!/usr/bin/env python3
"""Calibrated Ollama probe — system date injection vs raw date hallucination [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYSTEM = ROOT / "reports/ollama_gemma_local_system_prompt_v1.txt"
DEFAULT_OUT = ROOT / "reports/ollama_gemma_calibrated_probe_v1_latest.json"
PROBE_PROMPT = (
    "오늘 날짜가 몇 년 몇 월 몇 일인지 한 문장으로만 답해. "
    "구글 검색 가능 여부는 yes 또는 no 한 단어로만 답해."
)
MODELS = ("gemma4:12b", "gemma4:e2b")


def _local_date() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")


def _run_smoke(model: str, system_file: Path | None, out_json: Path) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/ollama_local_smoke_v1.py"),
        "--model",
        model,
        "--prompt",
        PROBE_PROMPT,
        "--out-json",
        str(out_json),
    ]
    if system_file:
        cmd.extend(["--system-file", str(system_file)])
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    doc = {}
    if out_json.is_file():
        doc = json.loads(out_json.read_text(encoding="utf-8"))
    doc["probe_exit_code"] = cp.returncode
    return doc


def _score(response: str, expected_date: str) -> dict:
    year = expected_date[:4]
    mentions_expected_year = year in response
    wrong_year = bool(re.search(r"20(2[0-3]|3[0-9])", response)) and year not in response
    claims_search_yes = bool(re.search(r"(?i)\byes\b|가능|할 수", response)) and "no" not in response.lower()
    denies_search = bool(re.search(r"(?i)\bno\b|불가|없", response))
    admits_no_date = bool(re.search(r"알 수 없|모르|cannot|can't|unable", response, re.I))
    return {
        "mentions_expected_year": mentions_expected_year,
        "likely_wrong_year": wrong_year,
        "claims_search_yes": claims_search_yes,
        "denies_search": denies_search,
        "admits_no_realtime_date": admits_no_date,
        "pass_heuristic": mentions_expected_year and denies_search and not claims_search_yes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--system-file", type=Path, default=DEFAULT_SYSTEM)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--models", nargs="*", default=list(MODELS))
    args = ap.parse_args()
    expected = _local_date()
    rows: list[dict] = []
    for model in args.models:
        raw_out = ROOT / "reports" / f"ollama_gemma_probe_raw_{model.replace(':', '_')}_latest.json"
        cal_out = ROOT / "reports" / f"ollama_gemma_probe_cal_{model.replace(':', '_')}_latest.json"
        raw = _run_smoke(model, None, raw_out)
        cal = _run_smoke(model, args.system_file, cal_out)
        rows.append(
            {
                "model": model,
                "expected_date": expected,
                "raw": {
                    "response_preview": raw.get("response_preview"),
                    "ok": raw.get("ok"),
                    "score": _score(raw.get("response_preview") or "", expected),
                },
                "calibrated": {
                    "response_preview": cal.get("response_preview"),
                    "ok": cal.get("ok"),
                    "system_preview": cal.get("system_preview"),
                    "score": _score(cal.get("response_preview") or "", expected),
                },
            }
        )
    doc = {
        "schema": "ollama_gemma_calibrated_probe_v1",
        "finished_at_utc": datetime.now(ZoneInfo("UTC")).isoformat(),
        "expected_date_asia_seoul": expected,
        "system_file": str(args.system_file),
        "hypothesis_tier": "B",
        "research_only": True,
        "not_operator_chat_replacement": True,
        "rows": rows,
        "verdict_ko": (
            "raw=날짜·검색 환각 위험; calibrated=system {{DATE}} 주입 시 개선 여부 비교. "
            "Track A·Oracle·BLS 판정은 스크립트/NIM만."
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    any_ok = any(r["calibrated"]["score"].get("pass_heuristic") for r in rows)
    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
