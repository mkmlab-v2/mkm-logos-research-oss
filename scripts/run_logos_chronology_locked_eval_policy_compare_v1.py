#!/usr/bin/env python3
"""Compare tier_v1 vs tier_v2_locked_eval on hardset v2 commander-signed gold ([HYPO])."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_chronology_locked_eval_policy_compare_v1_latest.json"


def _eval(gold: Path, policy: str, out: Path, tag_mode: str) -> dict[str, Any]:
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
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary: dict[str, Any] = {}
    if out.is_file():
        doc = json.loads(out.read_text(encoding="utf-8-sig"))
        summary = dict(doc.get("summary") or {})
        summary["status"] = doc.get("status")
    return {"exit_code": cp.returncode, "summary": summary, "output_json": str(out.relative_to(ROOT)).replace("\\", "/")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    art = ROOT / "docs/final/artifacts"
    steps = {
        "text_blind_tier_v1": _eval(
            args.gold_json,
            "tier_v1",
            art / "logos_chronology_hardset_text_blind_v2_tier_v1_baseline_eval_v1_latest.json",
            "text_blind",
        ),
        "text_blind_tier_v2": _eval(
            args.gold_json,
            "tier_v2_locked_eval",
            art / "logos_chronology_hardset_text_blind_v2_tier_v2_eval_v1_latest.json",
            "text_blind",
        ),
        "rag_assisted_tier_v2": _eval(
            args.gold_json,
            "tier_v2_locked_eval",
            art / "logos_chronology_hardset_rag_assisted_v2_tier_v2_eval_v1_latest.json",
            "rag_assisted",
        ),
    }

    def _pick(step: str, key: str) -> float | None:
        v = (steps[step].get("summary") or {}).get(key)
        return float(v) if v is not None else None

    compare = {
        "hit_at_1_delta_v2_minus_v1": (
            round(_pick("text_blind_tier_v2", "hit_at_1_strict") - _pick("text_blind_tier_v1", "hit_at_1_strict"), 6)
            if _pick("text_blind_tier_v2", "hit_at_1_strict") is not None
            and _pick("text_blind_tier_v1", "hit_at_1_strict") is not None
            else None
        ),
        "locked_eval_v1": _pick("text_blind_tier_v1", "locked_eval_hit_at_1_strict"),
        "locked_eval_v2_text_blind": _pick("text_blind_tier_v2", "locked_eval_hit_at_1_strict"),
        "locked_eval_v2_rag_assisted": _pick("rag_assisted_tier_v2", "locked_eval_hit_at_1_strict"),
        "rag_tier_v2_hit_at_1": _pick("rag_assisted_tier_v2", "hit_at_1_strict"),
    }

    ok = all(v.get("exit_code") == 0 for v in steps.values())
    doc = {
        "schema": "logos_chronology_locked_eval_policy_compare_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True},
        "ok": ok,
        "steps": steps,
        "compare": compare,
        "interpretation_ko": (
            "tier_v2_locked_eval: locked_eval risk-cluster에서 modern -0.14 / judges +0.12. "
            "MS/대외는 historical text_blind만. B→A·실매매 합선 없음."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "compare": compare}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
