#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tag_ratio(v: float) -> str:
    if v >= 0.67:
        return "HIGH"
    if v >= 0.34:
        return "MID"
    return "LOW"


def _tag_prob(v: float) -> str:
    if v >= 0.60:
        return "HIGH"
    if v >= 0.30:
        return "MID"
    return "LOW"


def _fmt_axis(axis: dict[str, float]) -> str:
    order = sorted(axis.items(), key=lambda kv: kv[1], reverse=True)
    return ", ".join(f"{k}={v:.3f}" for k, v in order)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build rule-based Sasang response from reasoning + baseline alerts.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--reasoning-json",
        type=Path,
        default=root / "reports" / "sasang_dna_market_reasoning_v1_latest.json",
    )
    ap.add_argument(
        "--baseline-json",
        type=Path,
        default=root / "reports" / "agct_sigma_locked_baseline_chain_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "sasang_rule_based_response_v1_latest.json",
    )
    ap.add_argument(
        "--output-md",
        type=Path,
        default=root / "reports" / "sasang_rule_based_response_v1_latest.md",
    )
    ap.add_argument(
        "--policy-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "sasang_response_formatting_policy_v1.json",
    )
    ap.add_argument(
        "--response-mode",
        choices=("dev", "prod"),
        default="prod",
    )
    ns = ap.parse_args()

    reasoning = _read_json(ns.reasoning_json)
    baseline = _read_json(ns.baseline_json)
    policy = _read_json(ns.policy_json)

    summary = reasoning.get("summary", {})
    latest_axis = summary.get("latest_fused_axis", {})
    byung = reasoning.get("byungjeungyakri_transition", {})
    byung_model = reasoning.get("byungjeungyakri_transition_model", {})
    interp = reasoning.get("interpretation_engine", {})
    decomp = interp.get("contribution_decomposition", {})

    baseline_summary = baseline.get("summary", {})
    baseline_status = str(baseline_summary.get("status", "UNKNOWN"))
    alert_reasons = list(baseline_summary.get("alert_reasons", []))
    winner_sigma = baseline_summary.get("h2h_winner_sigma")

    next_probs = byung_model.get("next_state_probabilities", {}) or {}
    next_rows = sorted(next_probs.items(), key=lambda kv: kv[1], reverse=True)

    geum_table = decomp.get("geumhwagyoyeok_contribution_table", []) or []
    bom_table = decomp.get("bomyeongjiju_contribution_table", []) or []

    conclusion = []
    conclusion.append(f"Baseline status={baseline_status}, winner_sigma={winner_sigma}")
    conclusion.append(f"Top axis={summary.get('latest_top_axis')} with fused axis [{_fmt_axis(latest_axis)}]")
    if alert_reasons:
        conclusion.append("ALERT reasons: " + ", ".join(alert_reasons))
    else:
        conclusion.append("No baseline alerts.")

    payload = {
        "schema": "sasang_rule_based_response_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "response_mode": ns.response_mode,
        "policy_ref": str(ns.policy_json.resolve()),
        "sections": {
            "four_axis_relation": {
                "latest_top_axis": summary.get("latest_top_axis"),
                "latest_fused_axis": latest_axis,
                "axis_relation_text": _fmt_axis(latest_axis),
            },
            "byungjeungyakri_transition": {
                "state": byung.get("state"),
                "transition_hint": byung.get("transition_hint"),
                "next_state_probabilities": [
                    {"state": s, "probability": p, "tag": _tag_prob(float(p))}
                    for s, p in next_rows
                ],
            },
            "geumhwagyoyeok_decomposition": [
                {
                    "factor": row.get("factor"),
                    "raw_value": row.get("raw_value"),
                    "contribution_ratio": row.get("contribution_ratio"),
                    "tag": _tag_ratio(float(row.get("contribution_ratio", 0.0))),
                }
                for row in geum_table
            ],
            "bomyeongjiju_decomposition": [
                {
                    "factor": row.get("factor"),
                    "raw_value": row.get("raw_value"),
                    "contribution_ratio": row.get("contribution_ratio"),
                    "tag": _tag_ratio(float(row.get("contribution_ratio", 0.0))),
                }
                for row in bom_table
            ],
            "conclusion": conclusion,
        },
        "mode_outputs": {},
    }

    top_state = next_rows[0][0] if next_rows else None
    top_prob = float(next_rows[0][1]) if next_rows else 0.0
    dev_output = {
        "input_evidence": {
            "reasoning_json": str(ns.reasoning_json.resolve()),
            "baseline_json": str(ns.baseline_json.resolve()),
            "latest_top_axis": summary.get("latest_top_axis"),
            "fused_axis": latest_axis,
        },
        "engine_summary": {
            "geumhwagyoyeok_factors": len(geum_table),
            "bomyeongjiju_factors": len(bom_table),
            "byungjeung_state": byung.get("state"),
            "byungjeung_top_next_state": top_state,
            "byungjeung_top_next_probability": top_prob,
        },
        "gate_decision": {
            "baseline_status": baseline_status,
            "winner_sigma": winner_sigma,
        },
        "blockers": alert_reasons,
    }
    prod_output = {
        "market_state": f"{summary.get('latest_top_axis')} axis dominant with structured stress monitoring",
        "confidence": {
            "baseline_status": baseline_status,
            "winner_sigma": winner_sigma,
            "next_state_top": top_state,
            "next_state_probability": round(top_prob, 4),
        },
        "action": "HOLD_AND_MONITOR" if baseline_status != "PASS" else "WATCH_CONFIRMATION",
        "disclaimer": "This output is a non-medical, non-guaranteed probabilistic scenario summary.",
    }
    payload["mode_outputs"]["dev"] = dev_output
    payload["mode_outputs"]["prod"] = prod_output

    md_lines = [
        "# Sasang Rule-Based Response v1",
        "",
        f"- generated_at_utc: {payload['generated_at_utc']}",
        f"- response_mode: {ns.response_mode}",
        f"- baseline_status: {baseline_status}",
        f"- winner_sigma: {winner_sigma}",
        "",
        "## 1) 4상 관계",
        f"- top_axis: {summary.get('latest_top_axis')}",
        f"- fused_axis: {_fmt_axis(latest_axis)}",
        "",
        "## 2) 병증약리 전변확률",
    ]
    for r in payload["sections"]["byungjeungyakri_transition"]["next_state_probabilities"]:
        md_lines.append(f"- {r['state']}: {r['probability']:.3f} ({r['tag']})")
    md_lines.extend(["", "## 3) 금화교역 분해"])
    for r in payload["sections"]["geumhwagyoyeok_decomposition"]:
        md_lines.append(f"- {r['factor']}: ratio={float(r['contribution_ratio']):.3f} ({r['tag']})")
    md_lines.extend(["", "## 4) 보명지주 분해"])
    for r in payload["sections"]["bomyeongjiju_decomposition"]:
        md_lines.append(f"- {r['factor']}: ratio={float(r['contribution_ratio']):.3f} ({r['tag']})")
    md_lines.extend(["", "## 5) 결론"])
    for c in conclusion:
        md_lines.append(f"- {c}")
    md_lines.extend(["", "## 6) Mode Output"])
    if ns.response_mode == "dev":
        md_lines.append("- mode: DEV (structured whitebox summary; no raw CoT)")
        md_lines.append(f"- evidence.reasoning_json: {dev_output['input_evidence']['reasoning_json']}")
        md_lines.append(f"- evidence.baseline_json: {dev_output['input_evidence']['baseline_json']}")
        md_lines.append(f"- engine.top_next_state: {dev_output['engine_summary']['byungjeung_top_next_state']}")
        md_lines.append(
            f"- gate: baseline_status={dev_output['gate_decision']['baseline_status']}, winner_sigma={dev_output['gate_decision']['winner_sigma']}"
        )
        if dev_output["blockers"]:
            md_lines.append(f"- blockers: {', '.join(dev_output['blockers'])}")
        else:
            md_lines.append("- blockers: none")
    else:
        md_lines.append("- mode: PROD (blackbox business response)")
        md_lines.append(f"- market_state: {prod_output['market_state']}")
        md_lines.append(f"- action: {prod_output['action']}")
        md_lines.append(f"- disclaimer: {prod_output['disclaimer']}")

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ns.output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()}")
    print(f"WROTE: {ns.output_md.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
