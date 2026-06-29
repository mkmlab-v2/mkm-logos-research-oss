#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extend B-track score panel + insight sidecar through holdout window [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)

DEFAULT_SCORE_OUT = ROOT / "reports/btrack_prophecy_score_science_core_panel_v1.json"
DEFAULT_SIDECAR_OUT = ROOT / "reports/btrack_prophecy_score_insight_sidecar_science_core_panel_v1.json"
DEFAULT_MARKET_SASANG_JSONL = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE_JSONL = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"
DEFAULT_LOGOS_PER_DATE_JSONL = ROOT / "reports/btrack_logos_per_date_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/science_core_extend_score_sidecar_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_score_rows(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = doc.get("rows") or []
    kospi = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "kospi"]
    dates = sorted({str(r.get("eval_date") or "")[:10] for r in kospi if r.get("eval_date")})
    return {
        "exists": True,
        "n_rows_total": len(rows),
        "n_kospi": len(kospi),
        "kospi_date_min": dates[0] if dates else None,
        "kospi_date_max": dates[-1] if dates else None,
    }


def run_extend(
    *,
    date_from: str,
    date_to: str,
    recent_trading_days: int,
    score_out: Path,
    sidecar_out: Path,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    logos_jsonl: Path,
    rebuild_market_sasang: bool,
    rebuild_manseryeok_myeongni: bool,
    rebuild_logos_per_date: bool,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    if rebuild_manseryeok_myeongni or not myeongni_jsonl.is_file():
        rc = subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts/build_btrack_myeongni_per_date_jsonl_v1.py"),
                "--date-from",
                date_from,
                "--date-to",
                date_to,
                "--out-jsonl",
                str(myeongni_jsonl),
            ],
            cwd=str(ROOT),
        )
        steps.append({"step": "build_myeongni_per_date", "exit_code": rc})
        if rc != 0:
            return {"ok": False, "steps": steps}

    if rebuild_market_sasang or not sasang_jsonl.is_file():
        rc = subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts/build_btrack_market_sasang_per_date_jsonl_v1.py"),
                "--date-from",
                date_from,
                "--date-to",
                date_to,
                "--refresh-market-psych-csv",
            ],
            cwd=str(ROOT),
        )
        steps.append({"step": "build_market_sasang_per_date", "exit_code": rc})
        if rc != 0:
            return {"ok": False, "steps": steps}

    if rebuild_logos_per_date or not logos_jsonl.is_file():
        rc = subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts/build_btrack_logos_per_date_jsonl_v1.py"),
                "--date-from",
                date_from,
                "--date-to",
                date_to,
                "--out-jsonl",
                str(logos_jsonl),
            ],
            cwd=str(ROOT),
        )
        steps.append({"step": "build_logos_per_date", "exit_code": rc})
        if rc != 0:
            return {"ok": False, "steps": steps}

    rc = subprocess.call(
        [
            sys.executable,
            str(ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"),
            "--recent-trading-days",
            str(recent_trading_days),
            "--panel-instrument",
            "multi",
            "--output",
            str(score_out),
        ],
        cwd=str(ROOT),
    )
    steps.append({"step": "build_prophecy_score_panel", "exit_code": rc, "output": str(score_out)})
    if rc != 0:
        return {"ok": False, "steps": steps}

    rc = subprocess.call(
        [
            sys.executable,
            str(ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"),
            "--score-json",
            str(score_out),
            "--out",
            str(sidecar_out),
            "--sasang-dynamics-jsonl",
            str(sasang_jsonl),
            "--myeongni-experiment-jsonl",
            str(myeongni_jsonl),
            "--logos-per-date-jsonl",
            str(logos_jsonl),
        ],
        cwd=str(ROOT),
    )
    steps.append({"step": "build_insight_sidecar", "exit_code": rc, "output": str(sidecar_out)})

    score_stats = _count_score_rows(score_out)
    sidecar_stats: dict[str, Any] = {"exists": sidecar_out.is_file()}
    if sidecar_out.is_file():
        sdoc = json.loads(sidecar_out.read_text(encoding="utf-8-sig"))
        feats = sdoc.get("per_date_features") or []
        kospi_feats = [f for f in feats if isinstance(f, dict) and str(f.get("instrument") or "").lower() == "kospi"]
        dates = sorted({str(f.get("eval_date") or "")[:10] for f in kospi_feats if f.get("eval_date")})
        sidecar_stats.update(
            {
                "n_per_date_features": len(feats),
                "n_kospi_features": len(kospi_feats),
                "kospi_date_min": dates[0] if dates else None,
                "kospi_date_max": dates[-1] if dates else None,
            }
        )

    holdout_overlap = bool(
        score_stats.get("kospi_date_max")
        and str(score_stats["kospi_date_max"]) >= "2026-05-01"
        and sidecar_stats.get("kospi_date_max")
        and str(sidecar_stats["kospi_date_max"]) >= "2026-05-01"
    )

    return {
        "schema": "science_core_extend_score_sidecar_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "target_window": {"from": date_from, "to": date_to},
        "paths": {
            "score_json": str(score_out.relative_to(ROOT)).replace("\\", "/"),
            "sidecar_json": str(sidecar_out.relative_to(ROOT)).replace("\\", "/"),
            "sasang_jsonl": str(sasang_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "myeongni_jsonl": str(myeongni_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "logos_jsonl": str(logos_jsonl.relative_to(ROOT)).replace("\\", "/"),
        },
        "score_stats": score_stats,
        "sidecar_stats": sidecar_stats,
        "holdout_may_overlap": holdout_overlap,
        "steps": steps,
        "ok": rc == 0,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--recent-trading-days", type=int, default=130)
    ap.add_argument("--score-out", type=Path, default=DEFAULT_SCORE_OUT)
    ap.add_argument("--sidecar-out", type=Path, default=DEFAULT_SIDECAR_OUT)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG_JSONL)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_PER_DATE_JSONL)
    ap.add_argument("--logos-jsonl", type=Path, default=DEFAULT_LOGOS_PER_DATE_JSONL)
    ap.add_argument("--rebuild-market-sasang", action="store_true")
    ap.add_argument("--rebuild-manseryeok-myeongni", action="store_true")
    ap.add_argument("--rebuild-logos-per-date", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args(argv)

    doc = run_extend(
        date_from=args.date_from,
        date_to=args.date_to,
        recent_trading_days=args.recent_trading_days,
        score_out=args.score_out,
        sidecar_out=args.sidecar_out,
        sasang_jsonl=args.sasang_jsonl,
        myeongni_jsonl=args.myeongni_jsonl,
        logos_jsonl=args.logos_jsonl,
        rebuild_market_sasang=args.rebuild_market_sasang,
        rebuild_manseryeok_myeongni=args.rebuild_manseryeok_myeongni,
        rebuild_logos_per_date=args.rebuild_logos_per_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} ok={doc.get('ok')} "
        f"score_max={((doc.get('score_stats') or {}).get('kospi_date_max'))} "
        f"sidecar_max={((doc.get('sidecar_stats') or {}).get('kospi_date_max'))}"
    )
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
