#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject symbol evidence fields into two-track Q&A pack.")
    ap.add_argument("--qa-json", default="docs/final/artifacts/two_track_qa_pack_latest.json")
    ap.add_argument(
        "--selector-json",
        default="docs/final/artifacts/multi_symbol_candidate_selector_latest.json",
    )
    ap.add_argument(
        "--fail-boundary-gate-json",
        default="docs/final/artifacts/two_track_fail_boundary_gate_latest.json",
    )
    ap.add_argument(
        "--falsification-json",
        default="docs/final/artifacts/two_track_falsification_suite_latest.json",
    )
    ap.add_argument(
        "--gematria-ablation-json",
        default="docs/final/artifacts/gematria_4d_ablation_latest.json",
    )
    ap.add_argument("--output-json", default="docs/final/artifacts/two_track_qa_pack_latest.json")
    args = ap.parse_args()

    qp = resolve(args.qa_json)
    sp = resolve(args.selector_json)
    gp = resolve(args.fail_boundary_gate_json)
    fp = resolve(args.falsification_json)
    apath = resolve(args.gematria_ablation_json)
    op = resolve(args.output_json)
    for p in (qp, sp, gp, fp, apath):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    qa = load(qp)
    sel = load(sp)
    gate = load(gp)
    falsification = load(fp)
    ablation = load(apath)
    selected = sel.get("selected") if isinstance(sel.get("selected"), list) else []
    top_symbol = selected[0] if selected else {}
    second_symbol = selected[1] if len(selected) > 1 else {}
    gate_eval = gate.get("gate_eval") if isinstance(gate.get("gate_eval"), dict) else {}
    should_trade = bool(gate_eval.get("should_trade", False))
    rollback = bool(gate_eval.get("rollback", True))
    reasons = gate_eval.get("reasons") if isinstance(gate_eval.get("reasons"), list) else []
    ab_snapshot = ablation.get("snapshot") if isinstance(ablation.get("snapshot"), dict) else {}
    checks = falsification.get("checks") if isinstance(falsification.get("checks"), list) else []
    checks_by_id = {str(c.get("id")): c for c in checks if isinstance(c, dict)}

    qna = qa.get("audience_qna") if isinstance(qa.get("audience_qna"), list) else []
    for audience_block in qna:
        if not isinstance(audience_block, dict):
            continue
        items = audience_block.get("items") if isinstance(audience_block.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            qid = str(item.get("question_id", "q1"))
            evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
            if qid == "q1":
                f3 = checks_by_id.get("F3", {})
                f4 = checks_by_id.get("F4", {})
                evidence["source_artifact"] = "two_track_falsification_suite_latest.json"
                evidence["metric_value"] = {
                    "f3_survivor_count": ((f3.get("detail") or {}).get("survivor_count")),
                    "f4_shift_score": ((f4.get("detail") or {}).get("shift_score")),
                    "f4_ci_low_defense_contrib": ((f4.get("detail") or {}).get("ci_low_defense_contrib")),
                }
            elif qid == "q2":
                evidence["source_artifact"] = "two_track_fail_boundary_gate_latest.json"
                evidence["metric_value"] = {
                    "should_trade": should_trade,
                    "rollback": rollback,
                    "reasons_count": len(reasons),
                }
            elif qid == "q3":
                evidence["source_artifact"] = "gematria_4d_ablation_latest.json"
                evidence["metric_value"] = {
                    "score_with_4d": ab_snapshot.get("score_with_4d"),
                    "score_without_4d": ab_snapshot.get("score_without_4d"),
                    "delta_with_minus_without": ab_snapshot.get("delta_with_minus_without"),
                }
            elif qid == "q4":
                evidence["source_artifact"] = "multi_symbol_candidate_selector_latest.json"
                evidence["metric_value"] = {
                    "top_symbol": top_symbol.get("seed_symbol"),
                    "top2_symbol": second_symbol.get("seed_symbol"),
                    "selected_count": sel.get("selected_count"),
                }
            else:  # q5 and fallback
                evidence["source_artifact"] = "two_track_fail_boundary_gate_latest.json"
                evidence["metric_value"] = {
                    "rollback": rollback,
                    "should_trade": should_trade,
                    "reasons": reasons,
                }
            evidence["as_of_utc"] = now()
            evidence["rollback_rule"] = "if fail_boundary_gate rollback=true then keep research_only and block promotion"
            evidence["gate_eval"] = {
                "pass": should_trade and not rollback,
                "should_trade": should_trade,
                "rollback": rollback,
                "reasons": reasons,
            }
            item["evidence"] = evidence

    qa["schema"] = "two_track_qa_pack_v2"
    qa["generated_at_utc"] = now()
    qa["defense_prompt_policy"] = {
        "require_evidence_fields": [
            "source_artifact",
            "metric_value",
            "as_of_utc",
            "rollback_rule",
            "gate_eval",
        ]
    }
    qa["symbol_evidence_overlay"] = {
        "selector_json": str(sp),
        "top_symbol": top_symbol.get("seed_symbol"),
        "top_coupling_strength": top_symbol.get("coupling_strength"),
        "falsification_json": str(fp),
        "gematria_ablation_json": str(apath),
    }
    qa["audience_qna"] = qna

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

