#!/usr/bin/env python3
"""P21 router regression bundle — P15 (no bloom rollback) + full gold fixture (B-track).

GraphRAG router hardening: adv3 + narrative eval + all gold_required materialize/eval.
Does not deepen resonance_cap or mutate bloom slice.

Reproducible:
  py scripts/run_logos_router_regression_bundle_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLD_FIXTURE = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
SLICE_ART = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
SLICE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"
GOLD_EVAL = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
OUT = ROOT / "reports/logos_router_regression_bundle_v1_latest.json"
MIN_BLOOM_CAP = 128
MIN_NARRATIVES = 200


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gold_required_ids() -> list[str]:
    doc = _load(GOLD_FIXTURE)
    return [str(i["id"]) for i in doc.get("items") or [] if i.get("eval_tier") == "gold_required"]


def _bloom_cap(path: Path) -> int:
    if not path.is_file():
        return 0
    return int(_load(path).get("resonance_cap") or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-materialize", action="store_true", help="Skip gold live materialize (eval only)")
    args = parser.parse_args()

    cap_before_art = _bloom_cap(SLICE_ART)
    cap_before_pub = _bloom_cap(SLICE_PUBLIC)
    steps: list[dict[str, Any]] = []

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_router_hit_pilot_p15_chain_v1.py",
            "--skip-pytest",
            "--skip-cdn-purge",
        ],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "p15_router_hit", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_router_hit_pilot_p15_chain_v1.py")

    cap_after_art = _bloom_cap(SLICE_ART)
    cap_after_pub = _bloom_cap(SLICE_PUBLIC)
    if cap_before_art and cap_after_art != cap_before_art:
        print(f"FAIL: artifact bloom cap changed {cap_before_art}->{cap_after_art}", file=sys.stderr)
        return 1
    if cap_before_pub and cap_after_pub != cap_before_pub:
        print(f"FAIL: public bloom cap changed {cap_before_pub}->{cap_after_pub}", file=sys.stderr)
        return 1
    if cap_after_art < MIN_BLOOM_CAP:
        print(f"FAIL: artifact bloom cap={cap_after_art} < {MIN_BLOOM_CAP}", file=sys.stderr)
        return 1

    eval_doc = _load(EVAL)
    if eval_doc.get("narrative_sample_count", 0) < MIN_NARRATIVES:
        print("FAIL: narrative_sample_count < 200", file=sys.stderr)
        return 1
    if eval_doc.get("summary", {}).get("router_hit_rate") != 1.0:
        print("FAIL: router_hit_rate != 1.0", file=sys.stderr)
        return 1

    gold_ids = _gold_required_ids()
    if not args.skip_materialize:
        mat_cmd = [sys.executable, "scripts/materialize_logos_gold_router_live_v1.py", "--promote-gold-prefix-first"]
        for qid in gold_ids:
            mat_cmd.extend(["--query-id", qid])
        proc = subprocess.run(mat_cmd, cwd=ROOT, check=False)
        steps.append({"step": "gold_materialize_all", "exit_code": proc.returncode, "query_ids": gold_ids})
        if proc.returncode != 0:
            return proc.returncode
        print(f"OK: materialize gold_required n={len(gold_ids)}")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_gold_query_eval_report_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "gold_eval_report", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_gold_query_eval_report_v1.py")

    gold = _load(GOLD_EVAL)
    if not (gold.get("summary") or {}).get("gold_required_all_pass"):
        print("FAIL: gold_required_all_pass false", file=sys.stderr)
        return 1

    rows = {str(r.get("id")): r for r in gold.get("rows") or []}
    for qid in ("q02", "q05"):
        hit1 = (rows.get(qid, {}).get("hit_at_k") or {}).get("1") or {}
        if not hit1.get("router"):
            print(f"FAIL: {qid} router hit@1 false", file=sys.stderr)
            return 1

    closure = _load(CLOSURE)
    if closure.get("narrative_sample_count", 0) < MIN_NARRATIVES:
        print("FAIL: closure narrative_sample_count < 200", file=sys.stderr)
        return 1

    report = {
        "schema": "logos_router_regression_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "chain_pass": True,
        "steps": steps,
        "bloom_cap": {"artifact": cap_after_art, "public": cap_after_pub, "unchanged": True},
        "narrative_eval": {
            "narrative_sample_count": eval_doc.get("narrative_sample_count"),
            "router_hit_rate": eval_doc.get("summary", {}).get("router_hit_rate"),
        },
        "gold_eval": {
            "gold_required_count": len(gold_ids),
            "gold_required_all_pass": True,
            "q02_router_hit_at_1": True,
            "q05_router_hit_at_1": True,
        },
        "closure_narratives": closure.get("narrative_sample_count"),
        "note": "Structural router/gold gates only; NOT prophecy accuracy or Track A KPI",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_router_regression_bundle_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest router regression bundle")

    print(
        f"chain_pass=true bloom_cap={cap_after_art} router_hit_rate=1.0 "
        f"gold_required_all_pass=true gold_n={len(gold_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
