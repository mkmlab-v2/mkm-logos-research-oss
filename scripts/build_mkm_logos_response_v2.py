#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_FRACTAL = ART / "logos_fractal_sign_reading_latest.json"
DEFAULT_COMPARE = ART / "logos_temporal_holdout_compare_backfill_latest.json"
DEFAULT_MONITOR = ART / "logos_backfill_dependence_monitor_latest.json"
DEFAULT_WEEKLY_ALERT = ART / "logos_pure_real_execution_gate_weekly_alert_latest.json"
DEFAULT_OUT = ART / "mkm_logos_response_v2_latest.json"
DEFAULT_NOTEBOOKLM_MANIFEST = ROOT / "docs" / "NotebookLM_sources_manifest.md"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _extract_core(fractal: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failed: list[str] = []
    top = fractal.get("top_match") if isinstance(fractal.get("top_match"), dict) else {}
    cur = fractal.get("current_vector_slkm") if isinstance(fractal.get("current_vector_slkm"), dict) else {}
    decision = fractal.get("decision") if isinstance(fractal.get("decision"), dict) else {}

    resonance = _f(top.get("resonance_cosine"), 0.0)
    if resonance <= 0.0:
        failed.append("top_resonance_missing")
    signal = str(decision.get("signal") or "WATCH")

    core = {
        "direction_core": round(_clip(_f(cur.get("K"), 0.5) * 2.0 - 1.0, -1.0, 1.0), 6),
        "confidence_core": round(_clip(resonance, 0.0, 1.0), 6),
        "archetype_resonance": round(resonance, 6),
        "top_archetype_id": str(top.get("archetype_id") or "unknown"),
        "signal_core": signal if signal in {"HOLD", "WATCH", "REDUCE"} else "WATCH",
    }
    return core, failed


def _coordinator_terms(
    compare: dict[str, Any], monitor: dict[str, Any], weekly: dict[str, Any], failed: list[str]
) -> tuple[dict[str, Any], list[str]]:
    delta = compare.get("delta_mixed_minus_pure")
    delta_status = str(monitor.get("status") or "")
    weekly_alert = bool(weekly.get("is_alert", False))

    confidence_term = 0.0
    if isinstance(delta, (int, float)):
        # lower delta is better; cap impact
        confidence_term = _clip((0.15 - float(delta)) * 0.3, -0.2, 0.2)
    else:
        failed.append("delta_missing")

    if delta_status not in {"PASS_LOW_BACKFILL_DEPENDENCE", "INSUFFICIENT_DATA"}:
        failed.append("backfill_monitor_not_pass")
    if weekly_alert:
        failed.append("weekly_alert_active")

    out = {
        "direction_override_allowed": False,
        "delta_confidence_term": round(confidence_term, 6),
        "weekly_alert_active": weekly_alert,
        "confidence_adjusted": 0.0,  # filled by caller
        "failed_check_keys": failed,
    }
    return out, failed


def _decision(signal_core: str, confidence_adj: float, failed: list[str], *, hold_cut: float) -> tuple[str, str]:
    if failed:
        return ("WATCH", "Coordinator checks not fully satisfied.")
    if confidence_adj < hold_cut:
        return ("WATCH", "Adjusted confidence below action threshold.")
    if signal_core == "REDUCE":
        return ("REDUCE", "Core signal and confidence are aligned.")
    if signal_core == "HOLD":
        return ("WATCH", "Core HOLD translated to WATCH-only policy mode.")
    return ("WATCH", "Stable watch posture.")


def _select_template(failed: list[str], decision: str) -> tuple[str, str]:
    if "weekly_alert_active" in failed:
        return ("risk_alert_watch", "주간 경보가 활성화되어 관측 강화(WATCH)와 수동 검토를 유지합니다.")
    if "backfill_monitor_not_pass" in failed:
        return ("backfill_risk_watch", "백필 의존성 리스크가 있어 신규 순수 실데이터 보강 전까지 WATCH를 유지합니다.")
    if "delta_missing" in failed:
        return ("missing_delta_watch", "핵심 delta 지표 누락으로 신뢰도 산출이 제한되어 WATCH로 유지합니다.")
    if decision == "REDUCE":
        return ("reduce_ready", "핵심 시그널과 조정 신뢰도가 정렬되어 REDUCE 시나리오를 검토할 수 있습니다.")
    return ("default_watch", "현재는 검증 우선 구간으로 WATCH를 유지하며 주기 재평가를 권장합니다.")


def _build_evidence_links(
    *,
    fractal_path: Path,
    compare_path: Path,
    monitor_path: Path,
    weekly_path: Path,
    extra_links: list[str],
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = [
        {"source_type": "artifact_json", "ref": str(fractal_path), "note": "fractal_sign_reading"},
        {"source_type": "artifact_json", "ref": str(compare_path), "note": "temporal_holdout_compare_backfill"},
        {"source_type": "artifact_json", "ref": str(monitor_path), "note": "backfill_dependence_monitor"},
        {"source_type": "artifact_json", "ref": str(weekly_path), "note": "execution_gate_weekly_alert"},
    ]
    if DEFAULT_NOTEBOOKLM_MANIFEST.is_file():
        links.append(
            {
                "source_type": "notebooklm_manifest",
                "ref": str(DEFAULT_NOTEBOOKLM_MANIFEST),
                "note": "notebooklm_sources_registry",
            }
        )
    for item in extra_links:
        links.append({"source_type": "external_ref", "ref": item, "note": "user_supplied"})
    return links


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MKM Logos response v2 (core + coordinator).")
    ap.add_argument("--fractal-json", type=Path, default=DEFAULT_FRACTAL)
    ap.add_argument("--compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--monitor-json", type=Path, default=DEFAULT_MONITOR)
    ap.add_argument("--weekly-alert-json", type=Path, default=DEFAULT_WEEKLY_ALERT)
    ap.add_argument("--track", choices=("A", "B"), default="B")
    ap.add_argument("--hold-confidence-cut", type=float, default=0.55)
    ap.add_argument("--failed-check-penalty", type=float, default=0.04)
    ap.add_argument("--evidence-link", action="append", default=[])
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fractal_path = args.fractal_json if args.fractal_json.is_absolute() else ROOT / args.fractal_json
    compare_path = args.compare_json if args.compare_json.is_absolute() else ROOT / args.compare_json
    monitor_path = args.monitor_json if args.monitor_json.is_absolute() else ROOT / args.monitor_json
    weekly_path = args.weekly_alert_json if args.weekly_alert_json.is_absolute() else ROOT / args.weekly_alert_json
    fractal = _read_json(fractal_path)
    compare = _read_json(compare_path)
    monitor = _read_json(monitor_path)
    weekly = _read_json(weekly_path)

    core, failed = _extract_core(fractal)
    coord, failed = _coordinator_terms(compare, monitor, weekly, failed)
    c_adj = _clip(core["confidence_core"] + coord["delta_confidence_term"] - (float(args.failed_check_penalty) * len(failed)), 0.0, 1.0)
    coord["confidence_adjusted"] = round(c_adj, 6)

    dec, reason = _decision(
        core["signal_core"],
        c_adj,
        failed,
        hold_cut=float(args.hold_confidence_cut),
    )
    template_key, template_text = _select_template(failed, dec)
    evidence_links = _build_evidence_links(
        fractal_path=fractal_path,
        compare_path=compare_path,
        monitor_path=monitor_path,
        weekly_path=weekly_path,
        extra_links=[str(x) for x in args.evidence_link],
    )

    out = {
        "schema": "mkm_logos_response_v2",
        "generated_at_utc": _now(),
        "track": args.track,
        "core_layer": core,
        "coordinator_layer": coord,
        "final_action": {"decision": dec, "reason": reason},
        "response_layer": {
            "template_key": template_key,
            "template_text": template_text,
            "failed_check_keys": failed,
            "next_reread_hours": 24 if dec == "WATCH" else 12,
        },
        "evidence_links": evidence_links,
        "governance": {
            "research_only": args.track == "B",
            "human_signoff_required": True,
            "action_policy_mode": "WATCH_FIRST",
        },
        "calibration": {
            "hold_confidence_cut": round(float(args.hold_confidence_cut), 6),
            "failed_check_penalty": round(float(args.failed_check_penalty), 6),
        },
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": dec}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

