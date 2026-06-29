#!/usr/bin/env python3
"""Promote hardset tier_v2 eval to SSOT primary; parallel eval lanes; digest merge ([HYPO])."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
DEFAULT_HIST_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_chronology_tier_v2_ssot_merge_v1_latest.json"

ART = ROOT / "docs/final/artifacts"
PRIMARY_SSOT = ART / "logos_chronology_hardset_text_blind_v2_eval_v1_latest.json"
TIER_V2_MIRROR = ART / "logos_chronology_hardset_text_blind_v2_tier_v2_eval_v1_latest.json"
RAG_TIER_V2 = ART / "logos_chronology_hardset_rag_assisted_v2_tier_v2_eval_v1_latest.json"
HIST_RAG_TIER_V2 = ART / "logos_chronology_era_blind_eval_rag_assisted_tier_v2_v1_latest.json"
REVAL = ART / "logos_symbolic_revalidation_report_latest.json"


def _eval(
    gold: Path,
    *,
    policy: str,
    tag_mode: str,
    out: Path,
    reval_key: str | None = None,
) -> dict[str, Any]:
    cmd = [
        PY,
        str(ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"),
        "--gold-json",
        str(gold),
        "--tag-mode",
        tag_mode,
        "--modern-boost",
        "0.08",
        "--boost-policy",
        policy,
        "--output-json",
        str(out),
    ]
    if reval_key:
        cmd.extend(["--append-revalidation", str(REVAL), "--revalidation-key", reval_key])
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary: dict[str, Any] = {}
    if out.is_file():
        doc = json.loads(out.read_text(encoding="utf-8-sig"))
        summary = dict(doc.get("summary") or {})
        summary["status"] = doc.get("status")
        summary["boost_policy"] = (doc.get("inputs") or {}).get("boost_policy")
    return {
        "exit_code": cp.returncode,
        "summary": summary,
        "output_json": str(out.relative_to(ROOT)).replace("\\", "/"),
        "stderr_tail": (cp.stderr or "")[-500:] if cp.returncode != 0 else "",
    }


def _promote_primary_from_tier_v2() -> dict[str, Any]:
    if not TIER_V2_MIRROR.is_file():
        return {"ok": False, "reason": "tier_v2_mirror_missing"}
    shutil.copy2(TIER_V2_MIRROR, PRIMARY_SSOT)
    doc = json.loads(PRIMARY_SSOT.read_text(encoding="utf-8-sig"))
    s = doc.get("summary") or {}
    return {
        "ok": True,
        "primary_ssot": str(PRIMARY_SSOT.relative_to(ROOT)).replace("\\", "/"),
        "hit_at_1_strict": s.get("hit_at_1_strict"),
        "boost_policy": (doc.get("inputs") or {}).get("boost_policy"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--historical-gold-json", type=Path, default=DEFAULT_HIST_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-historical-rag", action="store_true")
    args = ap.parse_args()

    parallel_jobs = {
        "hardset_text_blind_tier_v2": lambda: _eval(
            args.gold_json,
            policy="tier_v2_locked_eval",
            tag_mode="text_blind",
            out=TIER_V2_MIRROR,
        ),
        "hardset_rag_assisted_tier_v2": lambda: _eval(
            args.gold_json,
            policy="tier_v2_locked_eval",
            tag_mode="rag_assisted",
            out=RAG_TIER_V2,
        ),
    }
    if not args.skip_historical_rag:
        parallel_jobs["historical_rag_assisted_tier_v2"] = lambda: _eval(
            args.historical_gold_json,
            policy="tier_v2_locked_eval",
            tag_mode="rag_assisted",
            out=HIST_RAG_TIER_V2,
        )

    steps: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(parallel_jobs)) as pool:
        futures = {pool.submit(fn): name for name, fn in parallel_jobs.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            steps[name] = fut.result()

    promote = _promote_primary_from_tier_v2()

    cp_locked = subprocess.run(
        [PY, str(ROOT / "scripts/run_logos_chronology_locked_eval_policy_compare_v1.py"), "--gold-json", str(args.gold_json)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    steps["locked_eval_policy_compare"] = {"exit_code": cp_locked.returncode}

    cp_merge = subprocess.run(
        [PY, str(ROOT / "scripts/merge_logos_symbolic_revalidation_era_blocks_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    steps["merge_revalidation"] = {"exit_code": cp_merge.returncode}

    cp_digest = subprocess.run(
        [PY, str(ROOT / "scripts/build_logos_chronology_era_eval_digest_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    steps["digest"] = {"exit_code": cp_digest.returncode}

    locked_doc = None
    locked_path = ROOT / "reports/logos_chronology_locked_eval_policy_compare_v1_latest.json"
    if locked_path.is_file():
        locked_doc = json.loads(locked_path.read_text(encoding="utf-8-sig"))

    ok = bool(promote.get("ok")) and all(v.get("exit_code") == 0 for v in steps.values())

    doc = {
        "schema": "logos_chronology_tier_v2_ssot_merge_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True},
        "ok": ok,
        "ssot_contract": {
            "primary_hardset_eval": str(PRIMARY_SSOT.relative_to(ROOT)).replace("\\", "/"),
            "boost_policy": "tier_v2_locked_eval",
            "tier_v1_baseline_compare_only": "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_tier_v1_baseline_eval_v1_latest.json",
            "ms_citation_unchanged": "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json",
        },
        "promote": promote,
        "steps": steps,
        "locked_eval_compare": (locked_doc or {}).get("compare"),
        "interpretation_ko": (
            "hardset SSOT primary=tier_v2_locked_eval. tier_v1 baseline는 compare 전용. "
            "MS/대외는 historical text_blind tier_v1만. B→A·실매매 합선 없음."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "promote": promote, "locked_eval_compare": doc.get("locked_eval_compare")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
