#!/usr/bin/env python3
"""Build Stress Certified internal sales deck MD from spicy FSM + tune reports [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FSM = ROOT / "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json"
DEFAULT_TUNE = ROOT / "reports/wtt_dialog_risk_policy_tune_v1_latest.json"
DEFAULT_SALES = ROOT / "docs/final/artifacts/governed_ai_customization_sales_sheet_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/wtt_stress_certified_deck_v1_latest.md"
DEFAULT_META = ROOT / "reports/wtt_stress_certified_deck_v1_latest.json"
DEFAULT_RQ025_AUTO = ROOT / "reports/rq025_upstream_csv_auto_resolve_v1_latest.json"
DEFAULT_RQ025_THREE_ARM = ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json"
DEFAULT_OPERATOR_GATE = ROOT / "reports/wtt_operator_panel_gate_v1_latest.json"
DEFAULT_OPERATOR_FSM = ROOT / "reports/wtt_operator_panel_fsm_batch_v1_latest.json"
DEFAULT_OPERATOR_OBSERVE = ROOT / "reports/wtt_operator_panel_policy_observe_v1_latest.json"
DEFAULT_HUMAN_N30 = ROOT / "reports/wtt_human_n30_gate_v1_latest.json"
DEFAULT_CUSTOMER_FSM = ROOT / "reports/wtt_tenant_fsm_batch_wtt-customer-live-v1_v1_latest.json"
DEFAULT_CUSTOMER_INTAKE = ROOT / "data/wtt/intake/wtt-customer-live-v1.jsonl"
DEFAULT_COMPRESSION_BRIDGE = ROOT / "reports/wtt_compression_bridge_export_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pp_delta(x: Any) -> str:
    try:
        v = float(x) * 100
        return f"{v:+.1f}pp"
    except (TypeError, ValueError):
        return "—"


def _render_rq025_appendix(auto: dict[str, Any], three_arm: dict[str, Any]) -> list[str]:
    arms = {a.get("arm_id"): a for a in three_arm.get("arms") or [] if isinstance(a, dict)}
    proxy = arms.get("proxy") or {}
    upstream = arms.get("upstream") or {}
    resolved = auto.get("resolved") or {}
    pairwise = three_arm.get("pairwise_delta_holdout_ensemble_test") or {}
    best = (three_arm.get("verdict") or {}).get("best_arm_by_holdout") or "—"

    return [
        "## Appendix — Oracle RQ-025 λ bench (lane isolated · not WTT proof)",
        "",
        "_`[HYPO]` · `research_only` · `[NON_GATING]` · synthetic upstream substitute — not customer / production λ batch._",
        "",
        "**합성 데이터 기반 벤치 (inbox tail + proxy base):**",
        f"- proxy holdout L5: **{_pct(proxy.get('holdout_ensemble_test'))}** · upstream (synth): **{_pct(upstream.get('holdout_ensemble_test'))}**",
        f"- upstream − proxy: **{_pp_delta(pairwise.get('upstream_minus_proxy'))}** (negative = proxy better on holdout)",
        f"- best arm: **{best}** · `upstream_production_batch`: **{resolved.get('upstream_production_batch', False)}**",
        f"- source: `{resolved.get('source_kind', '—')}`",
        f"- Artifacts: `{DEFAULT_RQ025_AUTO.as_posix()}` · `{DEFAULT_RQ025_THREE_ARM.as_posix()}`",
        "- Track A · live · SEND: **HOLD** (majority gate not passed)",
        "",
    ]


def _render_operator_panel_section(
    gate: dict[str, Any],
    op_fsm: dict[str, Any],
    observe: dict[str, Any] | None,
) -> list[str]:
    gate_met = gate.get("operator_panel_n30_gate_met")
    collected = gate.get("operator_panel_sessions_collected")
    target = gate.get("target_n_sessions", 30)
    fsm_counts = op_fsm.get("fsm_state_counts") or {}
    mit = op_fsm.get("mitigation_counts") or {}
    lines = [
        "## Internal panel v0 (operator dogfood — not customer evidence)",
        "",
        "_`operator_panel` · `customer_provided=false` · `not_eligible_for_send=true` · **SEND HOLD**_",
        "",
        f"- Panel gate: **{collected}/{target}** · `operator_panel_n30_gate_met`: **{gate_met}**",
        f"- Provenance: `{gate.get('provenance_path', DEFAULT_OPERATOR_GATE.as_posix())}`",
        f"- Corpus: `{gate.get('intake_jsonl', 'data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl')}`",
        f"- Gate artifact: `{DEFAULT_OPERATOR_GATE.as_posix()}`",
        f"- FSM states (30 sessions): {fsm_counts}",
        f"- Mitigations: {mit}",
        f"- FSM artifact: `{DEFAULT_OPERATOR_FSM.as_posix()}`",
        "- One-click refresh: `scripts/Invoke-WttOperatorPanelDeckRefresh_v1.ps1`",
        "",
        "**Forbidden:** 실고객 n30·SEND·Track A 주장에 operator panel 사용 금지.",
        "",
    ]
    if observe:
        b = observe.get("baseline") or {}
        c = observe.get("candidate_v2") or {}
        lines.extend(
            [
                "**Policy observe (escalation-hint sessions, unlabeled):**",
                f"- baseline response rate: **{b.get('escalation_hint_response_rate', '—')}**",
                f"- candidate v2 response rate: **{c.get('escalation_hint_response_rate', '—')}**",
                f"- delta: **{observe.get('delta_escalation_hint_response_rate', '—')}**",
                f"- Artifact: `{DEFAULT_OPERATOR_OBSERVE.as_posix()}`",
                "",
            ]
        )
    return lines


def _render_customer_lane_section(
    human_gate: dict[str, Any],
    cust_fsm: dict[str, Any],
    bridge_meta: dict[str, Any] | None,
) -> list[str]:
    collected = human_gate.get("human_sessions_collected")
    target = human_gate.get("target_n_participants", 30)
    gate_met = human_gate.get("human_n30_gate_met")
    fsm_counts = cust_fsm.get("fsm_state_counts") or {}
    mit = cust_fsm.get("mitigation_counts") or {}
    lines = [
        "## Premium CS customer lane v0 (masked intake — curated pilot)",
        "",
        "_`customer_masked` · `research_only` · **SEND HOLD** · not recruited third-party panel claim_",
        "",
        f"- human_n30: **{collected}/{target}** · `human_n30_gate_met`: **{gate_met}**",
        f"- Intake: `{DEFAULT_CUSTOMER_INTAKE.as_posix()}`",
        f"- Gate artifact: `{DEFAULT_HUMAN_N30.as_posix()}`",
        f"- FSM states (30 sessions): {fsm_counts}",
        f"- Mitigations: {mit}",
        f"- FSM artifact: `{DEFAULT_CUSTOMER_FSM.as_posix()}`",
        "- Compression bridge (separate lane): `py scripts/export_wtt_sessions_to_compression_corpus_v1.py`",
        "",
        "**Forbidden:** operator_panel·stub·research_only 큐레이션을 실고객 SLA·SEND·Track A 증거로 승격 금지.",
        "",
    ]
    if bridge_meta:
        lines.extend(
            [
                "**Compression cross-lane (proxy ROI only):**",
                f"- Bridge rows: **{bridge_meta.get('row_count', '—')}**",
                f"- Artifact: `{bridge_meta.get('compression_jsonl', DEFAULT_COMPRESSION_BRIDGE.as_posix())}`",
                f"- Export meta: `{DEFAULT_COMPRESSION_BRIDGE.as_posix()}`",
                "",
            ]
        )
    return lines


def _render(
    fsm: dict[str, Any],
    tune: dict[str, Any],
    sales: dict[str, Any],
    *,
    rq025_appendix: list[str] | None = None,
    operator_appendix: list[str] | None = None,
    customer_appendix: list[str] | None = None,
) -> str:
    fsm_counts = fsm.get("fsm_state_counts") or {}
    mit = fsm.get("mitigation_counts") or {}
    baseline_hr = tune.get("baseline", {}).get("hit_rate")
    candidate_hr = tune.get("candidate", {}).get("hit_rate")
    disclaimers = (sales.get("required_disclaimers") or {}).get("ko") or []

    lines = [
        "# Stress Certified — Governed Persona Guard (internal deck)",
        "",
        f"_Generated: {_utc_now()} · `[HYPO]` · `research_only` · **SEND HOLD**_",
        "",
        "## Headline",
        "",
        sales.get("headline", {}).get("ko", ""),
        "",
        "## Proof (synthetic spicy 25 — not customer evidence)",
        "",
        f"- Sessions: **{fsm.get('session_count', '?')}**",
        f"- FSM states: {fsm_counts}",
        f"- Mitigations: {mit}",
        f"- Policy tune: baseline **{baseline_hr}** → candidate **{candidate_hr}** (synthetic labels)",
        f"- Artifact: `{DEFAULT_FSM.as_posix()}`",
        "",
        "## What we sell (ICP: Premium CS)",
        "",
        "- EPB band + dialog-risk FSM + masked intake — not prompt-only tuning",
        "- Escalation → cooldown / human handoff without persona collapse",
        "",
        "## Zero-Data → P0 path",
        "",
        "1. Internal demo: this deck + personadiary WTT UI",
        "2. Fill template: `data/wtt/templates/wtt_premium_cs_customer_masked_v1.template.jsonl`",
        "3. Intake 20–50 masked rows → `Run-WttPilotIntake_v1.ps1` (no stub/synthetic flags)",
        "4. Enrollment n30 → `check_wtt_human_n30_gate_v1.py --sync-pack`",
        "",
        "**Curated pilot (30/30):** `wtt-customer-live-v1` — see customer lane section below (`research_only`).",
        "**Internal dogfood:** `operator_panel` — `Invoke-WttOperatorPanelRoutine_v1.ps1` (not SEND-eligible).",
        "",
    ]
    if customer_appendix:
        lines.extend(customer_appendix)
    if operator_appendix:
        lines.extend(operator_appendix)
    if rq025_appendix:
        lines.extend(rq025_appendix)
    lines.extend(
        [
            "## Required disclaimers",
            "",
        ]
    )
    for d in disclaimers:
        lines.append(f"- {d}")
    lines.extend(
        [
            "",
            "## Forbidden headlines",
            "",
        ]
    )
    for f in sales.get("forbidden_in_deck") or []:
        lines.append(f"- {f}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fsm", type=Path, default=DEFAULT_FSM)
    ap.add_argument("--tune", type=Path, default=DEFAULT_TUNE)
    ap.add_argument("--sales", type=Path, default=DEFAULT_SALES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-out", type=Path, default=DEFAULT_META)
    ap.add_argument(
        "--include-rq025-appendix",
        action="store_true",
        help="Append Oracle RQ-025 synthetic lambda 3-arm bench (lane isolated)",
    )
    ap.add_argument("--rq025-auto-json", type=Path, default=DEFAULT_RQ025_AUTO)
    ap.add_argument("--rq025-three-arm-json", type=Path, default=DEFAULT_RQ025_THREE_ARM)
    ap.add_argument("--no-operator-panel", action="store_true", help="Omit operator panel section.")
    ap.add_argument("--operator-gate-json", type=Path, default=DEFAULT_OPERATOR_GATE)
    ap.add_argument("--operator-fsm-json", type=Path, default=DEFAULT_OPERATOR_FSM)
    ap.add_argument("--operator-observe-json", type=Path, default=DEFAULT_OPERATOR_OBSERVE)
    ap.add_argument("--no-customer-lane", action="store_true", help="Omit premium CS customer lane section.")
    ap.add_argument("--human-n30-json", type=Path, default=DEFAULT_HUMAN_N30)
    ap.add_argument("--customer-fsm-json", type=Path, default=DEFAULT_CUSTOMER_FSM)
    ap.add_argument("--compression-bridge-json", type=Path, default=DEFAULT_COMPRESSION_BRIDGE)
    args = ap.parse_args()

    fsm = _load(args.fsm)
    tune = _load(args.tune)
    sales = _load(args.sales)
    customer_appendix: list[str] | None = None
    customer_sources: dict[str, str] | None = None
    if not args.no_customer_lane:
        h_path = args.human_n30_json if args.human_n30_json.is_absolute() else ROOT / args.human_n30_json
        c_fsm_path = args.customer_fsm_json if args.customer_fsm_json.is_absolute() else ROOT / args.customer_fsm_json
        br_path = args.compression_bridge_json if args.compression_bridge_json.is_absolute() else ROOT / args.compression_bridge_json
        if h_path.is_file() and c_fsm_path.is_file():
            bridge = _load(br_path) if br_path.is_file() else None
            customer_appendix = _render_customer_lane_section(_load(h_path), _load(c_fsm_path), bridge)
            customer_sources = {
                "human_n30": str(h_path),
                "fsm": str(c_fsm_path),
                **({"bridge": str(br_path)} if bridge else {}),
            }

    operator_appendix: list[str] | None = None
    operator_sources: dict[str, str] | None = None
    if not args.no_operator_panel:
        gate_path = args.operator_gate_json if args.operator_gate_json.is_absolute() else ROOT / args.operator_gate_json
        fsm_path = args.operator_fsm_json if args.operator_fsm_json.is_absolute() else ROOT / args.operator_fsm_json
        obs_path = args.operator_observe_json if args.operator_observe_json.is_absolute() else ROOT / args.operator_observe_json
        if gate_path.is_file() and fsm_path.is_file():
            observe = _load(obs_path) if obs_path.is_file() else None
            operator_appendix = _render_operator_panel_section(_load(gate_path), _load(fsm_path), observe)
            operator_sources = {
                "gate": str(gate_path),
                "fsm": str(fsm_path),
                **({"observe": str(obs_path)} if observe else {}),
            }

    rq025_appendix: list[str] | None = None
    rq025_sources: dict[str, str] | None = None
    if args.include_rq025_appendix:
        auto_path = args.rq025_auto_json if args.rq025_auto_json.is_absolute() else ROOT / args.rq025_auto_json
        three_path = (
            args.rq025_three_arm_json if args.rq025_three_arm_json.is_absolute() else ROOT / args.rq025_three_arm_json
        )
        if not auto_path.is_file() or not three_path.is_file():
            raise SystemExit(f"RQ-025 appendix requires {auto_path} and {three_path}")
        rq025_appendix = _render_rq025_appendix(_load(auto_path), _load(three_path))
        rq025_sources = {"auto": str(auto_path), "three_arm": str(three_path)}

    md = _render(
        fsm,
        tune,
        sales,
        rq025_appendix=rq025_appendix,
        operator_appendix=operator_appendix,
        customer_appendix=customer_appendix,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")

    meta = {
        "schema": "wtt_stress_certified_deck_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "icp": "premium_cs",
        "out_md": str(args.out),
        "sources": {
            "fsm": str(args.fsm),
            "tune": str(args.tune),
            "sales": str(args.sales),
            **({"rq025": rq025_sources} if rq025_sources else {}),
            **({"operator_panel": operator_sources} if operator_sources else {}),
            **({"customer_lane": customer_sources} if customer_sources else {}),
        },
        "rq025_appendix_included": bool(rq025_appendix),
        "operator_panel_appendix_included": bool(operator_appendix),
        "customer_lane_appendix_included": bool(customer_appendix),
    }
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
