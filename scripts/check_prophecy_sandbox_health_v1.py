#!/usr/bin/env python3
"""Prophecy Sandbox ops health (artifact presence, chain ok, prod score isolation hint)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_NAME = "check_prophecy_sandbox_health_v1"
SENTRY_MONITOR_SLUG = "prophecy-sandbox-health-v1"
DEFAULT_CHAIN = ROOT / "reports/sandbox_prophecy_daily_chain_v1_latest.json"
DEFAULT_PANEL = ROOT / "reports/sandbox_prophecy_panel_v1_latest.json"
DEFAULT_STREAM = ROOT / "reports/sandbox_prophecy_stream_v1.jsonl"
DEFAULT_BRIDGE = ROOT / "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"
DEFAULT_ROLLUP = ROOT / "reports/sandbox_prophecy_rollup_v1_latest.json"
PROD_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_health_v1_latest.json"
DEFAULT_ARTIFACTS_VERIFY = ROOT / "reports/sandbox_prophecy_artifacts_verify_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def _max_calendar_days(rollup: dict[str, Any] | None) -> int:
    if not rollup:
        return 0
    best = 0
    for t in rollup.get("targets") or []:
        if isinstance(t, dict):
            try:
                best = max(best, int(t.get("n_calendar_days") or 0))
            except (TypeError, ValueError):
                pass
    return best


def build_health(
    *,
    chain: dict[str, Any] | None,
    chain_path: str | None,
    panel: dict[str, Any] | None,
    stream_path: Path,
    bridge: dict[str, Any] | None,
    rollup: dict[str, Any] | None,
    prod_score_path: Path,
    artifacts_verify: dict[str, Any] | None,
    strict: bool,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    checks["chain_report"] = {
        "path": chain_path,
        "exists": chain is not None,
        "ok": bool(chain and chain.get("ok")),
        "n_ok": chain.get("n_ok") if chain else None,
        "n_targets": chain.get("n_targets") if chain else None,
    }

    panel_ok = False
    if panel:
        n_ok = int(panel.get("n_ok") or sum(1 for t in panel.get("targets") or [] if t.get("ok")))
        n_tgt = len(panel.get("targets") or [])
        panel_ok = n_ok == n_tgt and n_tgt > 0
    checks["panel"] = {
        "exists": panel is not None,
        "ok": panel_ok,
        "n_targets": len(panel.get("targets") or []) if panel else 0,
    }

    stream_rows = 0
    sandbox_rows = 0
    if stream_path.is_file():
        for line in stream_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            stream_rows += 1
            try:
                o = json.loads(line)
                if o.get("hypothesis_tier") == "SANDBOX":
                    sandbox_rows += 1
            except json.JSONDecodeError:
                pass
    checks["stream"] = {
        "path": str(stream_path),
        "exists": stream_path.is_file(),
        "ok": stream_rows > 0 and sandbox_rows > 0,
        "n_rows": stream_rows,
        "n_sandbox_rows": sandbox_rows,
    }

    checks["bridge_draft"] = {
        "exists": bridge is not None,
        "ok": bool(
            bridge
            and bridge.get("status") == "DRAFT_BRIDGE_ONLY"
            and bridge.get("runtime_constraints", {}).get("prod_score_mutation") is False
        ),
        "n_total_draft_rows": bridge.get("n_total_draft_rows") if bridge else None,
    }

    max_days = _max_calendar_days(rollup)
    checks["rollup_progress"] = {
        "exists": rollup is not None,
        "max_n_calendar_days": max_days,
        "watchlist_ready": max_days >= 3,
        "holdout_likely_ready": max_days >= 4,
    }

    checks["prod_score"] = {
        "path": str(prod_score_path),
        "exists": prod_score_path.is_file(),
        "ok": prod_score_path.is_file(),
        "note_ko": "샌드박스 체인은 temp score만 쓰며 prod 본문을 덮어쓰지 않음(격벽).",
    }

    av_ok = bool(artifacts_verify and artifacts_verify.get("ok") is True)
    checks["artifacts_verify"] = {
        "exists": artifacts_verify is not None,
        "ok": av_ok,
        "n_missing": artifacts_verify.get("n_missing") if artifacts_verify else None,
        "n_bad_schema": artifacts_verify.get("n_bad_schema") if artifacts_verify else None,
    }

    required_ok = (
        checks["chain_report"]["ok"]
        and checks["panel"]["ok"]
        and checks["stream"]["ok"]
        and checks["bridge_draft"]["ok"]
        and checks["prod_score"]["ok"]
        and checks["artifacts_verify"]["ok"]
    )
    if strict:
        required_ok = required_ok and max_days >= 3

    return {
        "schema": "sandbox_prophecy_health_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "ok": required_ok,
        "strict_mode": strict,
        "checks": checks,
        "recommended_next": (
            "3일+ 스냅샷 축적 후 watchlist/holdout 재평가"
            if max_days < 3
            else "holdout pass 시 bridge tier_holdout_pass 휴먼 검토"
        ),
    }


def _run_main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain-json", type=Path, default=DEFAULT_CHAIN)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--stream-jsonl", type=Path, default=DEFAULT_STREAM)
    ap.add_argument("--bridge-json", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--rollup-json", type=Path, default=DEFAULT_ROLLUP)
    ap.add_argument("--prod-score-json", type=Path, default=PROD_SCORE)
    ap.add_argument("--artifacts-verify-json", type=Path, default=DEFAULT_ARTIFACTS_VERIFY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Also require max_n_calendar_days>=3")
    ap.add_argument(
        "--no-sentry",
        action="store_true",
        help="Skip Sentry crons and health-failure reporting",
    )
    args = ap.parse_args()

    doc = build_health(
        chain=_load(args.chain_json),
        chain_path=str(args.chain_json).replace("\\", "/"),
        panel=_load(args.panel_json),
        stream_path=args.stream_jsonl,
        bridge=_load(args.bridge_json),
        rollup=_load(args.rollup_json),
        prod_score_path=args.prod_score_json,
        artifacts_verify=_load(args.artifacts_verify_json),
        strict=args.strict,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"ok={doc['ok']} max_calendar_days={doc['checks']['rollup_progress']['max_n_calendar_days']}")

    if not args.no_sentry:
        try:
            from mkm_sentry_ops_v1 import capture_ops_health_failure

            capture_ops_health_failure(script=SCRIPT_NAME, doc=doc)
        except ImportError:
            pass

    return 0 if doc["ok"] else 1


def main() -> int:
    if "--no-sentry" in __import__("sys").argv:
        return _run_main()
    try:
        from mkm_sentry_ops_v1 import run_cron_job

        return run_cron_job(
            SENTRY_MONITOR_SLUG,
            _run_main,
            script=SCRIPT_NAME,
            mkm_hypothesis_tier="SANDBOX",
            mkm_research_only="true",
        )
    except ImportError:
        return _run_main()


if __name__ == "__main__":
    raise SystemExit(main())
