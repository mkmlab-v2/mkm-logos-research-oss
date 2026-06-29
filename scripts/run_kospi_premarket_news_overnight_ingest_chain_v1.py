#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI premarket ingest v2: dynamic queries · Exa · balance audit [HYPO]."""

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
OUT = ROOT / "reports/kospi_premarket_news_overnight_ingest_chain_v1_latest.json"
ART = ROOT / "docs/final/artifacts/kospi_premarket_news_overnight_ingest_chain_v1_latest.json"
PY = sys.executable
PREMARKET_CONFIG = ROOT / "data/commander/kospi_premarket_news_ingest_v1.json"
QUERY_PLAN = ROOT / "reports/kospi_premarket_dynamic_query_plan_v1_latest.json"
EXA_JSONL = ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _run(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "optional": optional,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-500:],
    }


def _resolve_query_plan(config_path: Path) -> dict[str, Any]:
    from scripts.kospi_premarket_dynamic_query_lib_v1 import load_config, resolve_premarket_news_queries

    cfg = load_config(config_path)
    if not cfg:
        return {}
    plan = resolve_premarket_news_queries(cfg)
    QUERY_PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_premarket_dynamic_query_plan_v1_latest.json"
    art.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-fetch-indices", action="store_true")
    ap.add_argument("--skip-naver", action="store_true")
    ap.add_argument("--skip-exa", action="store_true")
    ap.add_argument("--allow-naver-cache-fallback", action="store_true")
    ap.add_argument("--premarket-config", type=Path, default=PREMARKET_CONFIG)
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    steps: list[dict[str, Any]] = []
    cfg = _read_json(ns.premarket_config)
    plan = _resolve_query_plan(ns.premarket_config)
    steps.append(
        {
            "name": "resolve_dynamic_query_plan",
            "cmd": ["internal", "kospi_premarket_dynamic_query_lib_v1"],
            "exit_code": 0 if plan else 1,
            "optional": False,
            "tail": json.dumps(
                {
                    "news_queries": plan.get("news_queries_resolved"),
                    "exa_queries": plan.get("exa_queries_resolved"),
                    "context": plan.get("context"),
                },
                ensure_ascii=False,
            )[-500:],
        }
    )

    if not ns.skip_fetch_indices:
        steps.append(
            _run(
                "fetch_global_overnight_indices_yfinance",
                [PY, "scripts/fetch_global_overnight_indices_yfinance_v1.py"],
                optional=True,
            )
        )

    if not ns.skip_naver:
        naver_cmd = [
            PY,
            "scripts/fetch_naver_openapi_signals_v1.py",
            "--profile",
            "kospi_premarket",
            "--premarket-config",
            str(ns.premarket_config),
        ]
        if ns.allow_naver_cache_fallback:
            naver_cmd.append("--allow-cache-fallback")
        steps.append(_run("fetch_naver_kospi_premarket_news", naver_cmd, optional=True))

    if not ns.skip_exa:
        exa_queries = plan.get("exa_queries_resolved") or cfg.get("exa_queries") or []
        per_q = int(cfg.get("exa_num_results_per_query") or 6)
        has_key = bool(os.environ.get("EXA_API_KEY", "").strip())
        for i, qtext in enumerate(exa_queries):
            if not str(qtext).strip():
                continue
            cmd = [
                PY,
                "scripts/fetch_exa_macro_news_observation_v1.py",
                "--query",
                str(qtext),
                "--num-results",
                str(per_q),
                "--output",
                str(EXA_JSONL),
            ]
            if i > 0:
                cmd.append("--append")
            if not has_key:
                steps.append(
                    {
                        "name": f"fetch_exa_skipped_no_key_{i}",
                        "cmd": cmd,
                        "exit_code": 0,
                        "optional": True,
                        "tail": "EXA_API_KEY unset — skipped (tier_0)",
                    }
                )
                break
            steps.append(_run(f"fetch_exa_macro_news_{i}", cmd, optional=True))

    steps.append(
        _run(
            "build_global_market_overnight_signals",
            [
                PY,
                "scripts/build_global_market_overnight_signals_v1.py",
                "--pre-news-input",
                "docs/final/artifacts/pre_news_shadow_input_latest.json",
            ],
        )
    )
    steps.append(
        _run(
            "build_news_macro_lens_adapters",
            [PY, "scripts/build_btrack_news_macro_lens_adapters_v1.py"],
        )
    )
    steps.append(
        _run(
            "build_premarket_ingest_balance_audit",
            [PY, "scripts/build_kospi_premarket_ingest_balance_audit_v1.py", "--query-plan", str(QUERY_PLAN)],
        )
    )

    required_fail = [s for s in steps if not s.get("optional") and s["exit_code"] != 0]
    doc = {
        "schema": "kospi_premarket_news_overnight_ingest_chain_v2",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "hd_delegation": "tier_0_balanced_ingest_v2",
        "premarket_config": str(ns.premarket_config),
        "quality_ok": not required_fail,
        "steps": steps,
        "artifacts": {
            "premarket_config": "data/commander/kospi_premarket_news_ingest_v1.json",
            "dynamic_query_plan": "reports/kospi_premarket_dynamic_query_plan_v1_latest.json",
            "balance_audit": "reports/kospi_premarket_ingest_balance_audit_v1_latest.json",
            "naver_news_feed": "docs/final/artifacts/naver_news_feed_latest.json",
            "pre_news_shadow_input": "docs/final/artifacts/pre_news_shadow_input_latest.json",
            "exa_news_jsonl": "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
            "global_overnight": "docs/final/artifacts/global_market_overnight_signals_v1_latest.json",
            "news_lens": "docs/final/artifacts/news_independent_lens_latest.json",
            "macro_lens": "docs/final/artifacts/macro_independent_lens_latest.json",
        },
        "reproduce": "py scripts/run_kospi_premarket_news_overnight_ingest_chain_v1.py --allow-naver-cache-fallback",
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["quality_ok"], "schema": doc["schema"]}, ensure_ascii=False))
    return 1 if required_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
