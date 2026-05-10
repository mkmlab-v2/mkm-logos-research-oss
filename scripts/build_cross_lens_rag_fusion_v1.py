#!/usr/bin/env python3
"""Build cross-lens RAG fusion report and markdown dashboard (Track B only).

Lens rows: myeongni, sasang, logos, optional market_myeongni overlay, optional market_sasang.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOGOS_WEALTH = ROOT / "docs" / "final" / "artifacts" / "logos_ann_query_wealth_transfer_latest.json"
DEFAULT_LOGOS_JUSTICE = ROOT / "docs" / "final" / "artifacts" / "logos_ann_query_justice_weights_latest.json"
DEFAULT_LOGOS_EMPIRE = ROOT / "docs" / "final" / "artifacts" / "logos_ann_query_empire_cycle_latest.json"
DEFAULT_FUSION_STUB = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"
DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_LOGOS_LENS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"
DEFAULT_MARKET_SASANG_LENS = ROOT / "docs" / "final" / "artifacts" / "market_sasang_lens_latest.json"
DEFAULT_MARKET_MYEONGNI_LENS = ROOT / "docs" / "final" / "artifacts" / "market_myeongni_lens_latest.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_fusion_latest.json"
DEFAULT_OUT_MD = ROOT / "reports" / "cross_lens_rag_fusion_latest.md"
DEFAULT_HISTORY_JSONL = ROOT / "reports" / "cross_lens_rag_fusion_history.jsonl"
DEFAULT_ALERT_JSON = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_alert_latest.json"
DEFAULT_ALERT_LOG_JSONL = ROOT / "reports" / "cross_lens_rag_alert_log.jsonl"

LENS_MUSIC_GATE_CHAIN_SCHEMA = "lens_music_gate_chain_v1"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pick_sign(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def _lens_snapshot(name: str, path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": name,
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
            "artifact_path": str(path.resolve()),
        }
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    score = _safe_float(scores.get("direction_score"))
    conf = max(0.0, min(1.0, _safe_float(scores.get("confidence"))))
    return {
        "lens_id": str(doc.get("lens_id") or name),
        "available": True,
        "direction_score": score,
        "confidence": conf,
        "direction_sign": _pick_sign(score),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
        "schema": doc.get("schema"),
    }


def _market_myeongni_lens_snapshot(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": "market_myeongni",
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
            "artifact_path": str(path.resolve()),
        }
    if str(doc.get("schema")) != "market_myeongni_lens_v1":
        return {
            "lens_id": "market_myeongni",
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
            "artifact_path": str(path.resolve()),
            "note": "schema mismatch",
        }
    return _lens_snapshot("market_myeongni", path)


def _lens_music_gate_chain_passthrough(path: Path | None, *, enabled: bool) -> dict[str, Any] | None:
    """Optional symbolic-audio gate chain JSON — 관측 패스스루; cross-lens 합의 행렬에 포함하지 않음."""
    if not enabled or path is None:
        return None
    doc = _read_json(path)
    if not doc:
        return {
            "schema": "cross_lens_lens_music_passthrough_v1",
            "available": False,
            "artifact_path": str(path.resolve()),
            "non_gating": True,
            "note": "file missing or invalid JSON",
        }
    schema_ok = str(doc.get("schema") or "") == LENS_MUSIC_GATE_CHAIN_SCHEMA
    out: dict[str, Any] = {
        "schema": "cross_lens_lens_music_passthrough_v1",
        "available": schema_ok,
        "upstream_schema": doc.get("schema"),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
        "non_gating": True,
        "passthrough": {
            "final_decision": doc.get("final_decision"),
            "emotion_overlay_stage": doc.get("emotion_overlay_stage"),
            "quality_guard_m7": doc.get("quality_guard_m7"),
        },
    }
    return out


def _market_sasang_snapshot(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": "market_sasang",
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
            "artifact_path": str(path.resolve()),
        }
    if str(doc.get("schema")) != "market_sasang_lens_v1":
        return {
            "lens_id": "market_sasang",
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
            "artifact_path": str(path.resolve()),
            "note": "schema mismatch",
        }
    fb = doc.get("fusion_bridge") if isinstance(doc.get("fusion_bridge"), dict) else {}
    unc = doc.get("uncertainty") if isinstance(doc.get("uncertainty"), dict) else {}
    veto = doc.get("veto") if isinstance(doc.get("veto"), dict) else {}
    score = max(-1.0, min(1.0, _safe_float(fb.get("score_hint"))))
    comp_unc = max(0.0, min(1.0, _safe_float(unc.get("composite_uncertainty"), 0.5)))
    conf = max(0.0, min(1.0, 1.0 - comp_unc))
    if bool(veto.get("force_hold")):
        conf *= 0.25
    return {
        "lens_id": "market_sasang",
        "available": True,
        "direction_score": score,
        "confidence": round(conf, 6),
        "direction_sign": _pick_sign(score),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
        "schema": doc.get("schema"),
        "veto_force_hold": bool(veto.get("force_hold")),
        "veto_reason_codes": list(veto.get("reason_codes") or []),
    }


def _theme_snapshot(theme: str, path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "theme": theme,
            "available": False,
            "top_count": 0,
            "avg_score_top5": 0.0,
            "top_verse_ids": [],
            "artifact_path": str(path.resolve()),
        }
    top_k = doc.get("top_k") if isinstance(doc.get("top_k"), list) else []
    top_verse_ids: list[str] = []
    top_scores: list[float] = []
    for row in top_k[:5]:
        if isinstance(row, dict):
            vid = row.get("verse_id")
            if vid:
                top_verse_ids.append(str(vid))
            top_scores.append(_safe_float(row.get("score")))
    avg_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
    return {
        "theme": theme,
        "available": True,
        "top_count": len(top_k),
        "avg_score_top5": round(avg_score, 6),
        "top_verse_ids": top_verse_ids,
        "embedding_mode": doc.get("embedding_mode"),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
    }


def _build_conflict_matrix(lens_rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in lens_rows if r.get("available")]
    sign_counts = {"bull": 0, "bear": 0, "neutral": 0}
    for row in active:
        sign_counts[str(row.get("direction_sign", "neutral"))] += 1
    majority = max(sign_counts, key=sign_counts.get) if active else "neutral"
    minority = [
        str(r.get("lens_id"))
        for r in active
        if str(r.get("direction_sign", "neutral")) != majority
    ]
    return {
        "active_count": len(active),
        "majority_sign": majority,
        "sign_counts": sign_counts,
        "minority_lenses": minority,
        "agreement_rate": round((sign_counts[majority] / len(active)) if active else 0.0, 6),
    }


def _build_final_gate(conflict: dict[str, Any], fusion_stub: dict[str, Any] | None) -> dict[str, Any]:
    veto = False
    veto_reasons: list[str] = []
    if conflict.get("agreement_rate", 0.0) < 0.67:
        veto = True
        veto_reasons.append("LOW_CROSS_LENS_AGREEMENT")
    if isinstance(fusion_stub, dict):
        cs = fusion_stub.get("consensus") if isinstance(fusion_stub.get("consensus"), dict) else {}
        if cs.get("consensus_sign") == "neutral":
            veto = True
            veto_reasons.append("NEUTRAL_CONSENSUS_SIGN")
    return {
        "schema": "human_commander_gate_v1",
        "track": "B",
        "non_gating": True,
        "veto_force_hold": veto,
        "veto_reason_codes": veto_reasons,
        "final_authority": "human_commander",
        "machine_output_role": "decision_support_observation_only",
    }


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    themes = payload["themes"]
    conflict = payload["cross_lens_conflict_matrix"]
    gate = payload["final_gate_panel"]
    lines = [
        "# Cross-Lens RAG Fusion Dashboard (Track B)",
        "",
        f"- generated_at_utc: {payload['ts_utc']}",
        f"- logos_index_rows: {payload.get('logos_index_rows', 'unknown')}",
        f"- majority_sign: {conflict['majority_sign']}",
        f"- agreement_rate: {conflict['agreement_rate']}",
        "",
        "## Lens Evidence Map",
        "",
    ]
    for row in payload["lens_snapshots"]:
        lines.append(
            f"- {row['lens_id']}: sign={row['direction_sign']}, score={row['direction_score']:.6f}, conf={row['confidence']:.6f}"
        )
    ax = payload.get("sasang_b_track_axis_scores_v1")
    lines += ["", "## Sasang `b_track_axis_scores_v1` (dynamics proxies only)", ""]
    if isinstance(ax, dict) and str(ax.get("schema")) == "sasang_b_track_axis_scores_v1":
        lines += [
            "| field | value |",
            "|-------|-------|",
            f"| heat_proxy | {ax.get('heat_proxy')} |",
            f"| cold_proxy | {ax.get('cold_proxy')} |",
            f"| volatility_rarefaction_proxy | {ax.get('volatility_rarefaction_proxy')} |",
            f"| thermal_imbalance_proxy | {ax.get('thermal_imbalance_proxy')} |",
            "",
        ]
        if ax.get("disclaimer_ko"):
            lines.append(f"> {ax['disclaimer_ko']}")
            lines.append("")
    else:
        lines.append(
            "_No `b_track_axis_scores_v1` in `sasang_independent_lens_latest.json` — run `scripts/run_lens_sasang.py` (v0.2.0+)._"
        )
        lines.append("")
    lm = payload.get("lens_music_symbolic_passthrough_v1")
    lines += ["", "## Lens music (symbolic gate chain, passthrough)", ""]
    if isinstance(lm, dict) and lm.get("available"):
        pd = lm.get("passthrough") if isinstance(lm.get("passthrough"), dict) else {}
        lines.append(
            f"- upstream_schema={lm.get('upstream_schema')}, ts={lm.get('artifact_ts_utc')}, "
            f"final_decision={pd.get('final_decision')}"
        )
        lines.append("")
        lines.append(
            "_Passthrough only; excluded from cross-lens agreement matrix. Track B / non-gating._"
        )
    elif isinstance(lm, dict):
        lines.append(f"- path={lm.get('artifact_path')}, available=false ({lm.get('note', 'schema or parse')})")
        lines.append("")
    else:
        lines.append("_No lens music gate-chain JSON supplied (`--lens-music-gate-chain-json`)._")
        lines.append("")
    lines += ["", "## Theme Retrieval Summary", ""]
    for th in themes:
        anchors = ", ".join(th["top_verse_ids"]) if th["top_verse_ids"] else "n/a"
        lines.append(
            f"- {th['theme']}: top_count={th['top_count']}, avg_score_top5={th['avg_score_top5']}, anchors={anchors}"
        )
    lines += [
        "",
        "## Final Gate Panel",
        "",
        f"- non_gating: {gate['non_gating']}",
        f"- veto_force_hold: {gate['veto_force_hold']}",
        f"- veto_reason_codes: {', '.join(gate['veto_reason_codes']) if gate['veto_reason_codes'] else 'none'}",
        "",
        "> Observation-only output. Do not auto-route to A-track execution.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    gate = payload.get("final_gate_panel", {})
    reasons = gate.get("veto_reason_codes") if isinstance(gate, dict) else []
    if not isinstance(reasons, list):
        reasons = []
    row = {
        "ts_utc": payload.get("ts_utc"),
        "majority_sign": payload.get("cross_lens_conflict_matrix", {}).get("majority_sign"),
        "agreement_rate": payload.get("cross_lens_conflict_matrix", {}).get("agreement_rate"),
        "veto_force_hold": payload.get("final_gate_panel", {}).get("veto_force_hold"),
        "veto_reason_codes": [str(x) for x in reasons],
        "bull_count": payload.get("cross_lens_conflict_matrix", {}).get("sign_counts", {}).get("bull"),
        "bear_count": payload.get("cross_lens_conflict_matrix", {}).get("sign_counts", {}).get("bear"),
        "neutral_count": payload.get("cross_lens_conflict_matrix", {}).get("sign_counts", {}).get("neutral"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_last_history_row(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _build_signal_light(payload: dict[str, Any]) -> dict[str, Any]:
    conflict = payload.get("cross_lens_conflict_matrix", {})
    gate = payload.get("final_gate_panel", {})
    delta = payload.get("delta_from_prev", {})

    agreement = _safe_float(conflict.get("agreement_rate"))
    veto = bool(gate.get("veto_force_hold"))
    d_agree = _safe_float(delta.get("agreement_rate_delta"))
    d_bear = _safe_float(delta.get("bear_ratio_delta"))

    if veto or agreement < 0.5:
        status = "RED"
        note = "Hold / manual review required."
    elif agreement < 0.67 or d_agree < -0.1 or d_bear > 0.2:
        status = "YELLOW"
        note = "Caution: conflict or drift rising."
    else:
        status = "GREEN"
        note = "Observation stream stable."

    return {
        "schema": "signal_light_v1",
        "status": status,
        "agreement_rate": round(agreement, 6),
        "veto_force_hold": veto,
        "agreement_rate_delta": round(d_agree, 6),
        "bear_ratio_delta": round(d_bear, 6),
        "note": note,
    }


def _emit_alert_if_needed(
    payload: dict[str, Any],
    alert_json: Path,
    alert_log_jsonl: Path,
    *,
    always_emit: bool,
) -> bool:
    signal = payload.get("signal_light", {})
    status = str(signal.get("status", "YELLOW")).upper()
    if status == "GREEN" and not always_emit:
        return False
    alert_obj = {
        "schema": "cross_lens_rag_alert_v1",
        "ts_utc": payload.get("ts_utc"),
        "status": status,
        "track": "B",
        "non_gating": True,
        "always_emit": bool(always_emit),
        "signal_light": signal,
        "cross_lens_conflict_matrix": payload.get("cross_lens_conflict_matrix", {}),
        "final_gate_panel": payload.get("final_gate_panel", {}),
        "delta_from_prev": payload.get("delta_from_prev", {}),
    }
    alert_json.parent.mkdir(parents=True, exist_ok=True)
    alert_json.write_text(json.dumps(alert_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    alert_log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with alert_log_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert_obj, ensure_ascii=False) + "\n")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Build cross-lens RAG fusion report and dashboard.")
    ap.add_argument("--logos-wealth", type=Path, default=DEFAULT_LOGOS_WEALTH)
    ap.add_argument("--logos-justice", type=Path, default=DEFAULT_LOGOS_JUSTICE)
    ap.add_argument("--logos-empire", type=Path, default=DEFAULT_LOGOS_EMPIRE)
    ap.add_argument("--fusion-stub", type=Path, default=DEFAULT_FUSION_STUB)
    ap.add_argument("--myeongni-lens", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang-lens", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--market-sasang-lens", type=Path, default=DEFAULT_MARKET_SASANG_LENS)
    ap.add_argument("--market-myeongni-lens", type=Path, default=DEFAULT_MARKET_MYEONGNI_LENS)
    ap.add_argument(
        "--no-market-sasang",
        action="store_true",
        help="Exclude market_sasang_lens_v1 from cross-lens conflict matrix.",
    )
    ap.add_argument(
        "--no-market-myeongni",
        action="store_true",
        help="Exclude market_myeongni_lens_v1 overlay from cross-lens conflict matrix.",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY_JSONL)
    ap.add_argument(
        "--skip-history-append",
        action="store_true",
        help="Do not append a snapshot row to history jsonl.",
    )
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT_JSON)
    ap.add_argument("--alert-log-jsonl", type=Path, default=DEFAULT_ALERT_LOG_JSONL)
    ap.add_argument(
        "--skip-alert-emit",
        action="store_true",
        help="Do not emit alert artifacts for YELLOW/RED signal lights.",
    )
    ap.add_argument(
        "--always-emit-alert",
        action="store_true",
        help="Emit alert JSON + append log every run (including GREEN heartbeat).",
    )
    ap.add_argument(
        "--force-signal-light",
        choices=["GREEN", "YELLOW", "RED"],
        default=None,
        help="Override computed signal_light.status for CI/manual verification (sets signal_light.forced=true).",
    )
    ap.add_argument(
        "--lens-music-gate-chain-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional lens_music_gate_chain_v1 JSON (observation passthrough; not merged into agreement matrix).",
    )
    ap.add_argument(
        "--no-lens-music",
        action="store_true",
        help="Ignore --lens-music-gate-chain-json even if set.",
    )
    args = ap.parse_args()

    themes = [
        _theme_snapshot("wealth_transfer", args.logos_wealth),
        _theme_snapshot("justice_measures", args.logos_justice),
        _theme_snapshot("empire_cycle", args.logos_empire),
    ]
    lens_snapshots = [
        _lens_snapshot("myeongni", args.myeongni_lens),
        _lens_snapshot("sasang", args.sasang_lens),
        _lens_snapshot("logos", args.logos_lens),
    ]
    if not args.no_market_myeongni:
        lens_snapshots.append(_market_myeongni_lens_snapshot(args.market_myeongni_lens))
    if not args.no_market_sasang:
        lens_snapshots.append(_market_sasang_snapshot(args.market_sasang_lens))
    fusion_stub = _read_json(args.fusion_stub)
    conflict = _build_conflict_matrix(lens_snapshots)
    bull_count = float(conflict.get("sign_counts", {}).get("bull", 0))
    bear_count = float(conflict.get("sign_counts", {}).get("bear", 0))
    neutral_count = float(conflict.get("sign_counts", {}).get("neutral", 0))
    total_count = max(1.0, bull_count + bear_count + neutral_count)
    curr_bull_ratio = bull_count / total_count
    curr_bear_ratio = bear_count / total_count

    logos_index_rows: int | None = None
    logos_build = _read_json(ROOT / "docs" / "final" / "artifacts" / "logos_vector_index_ann_lite_v1_latest.json")
    if isinstance(logos_build, dict):
        rw = logos_build.get("rows_written")
        if isinstance(rw, int):
            logos_index_rows = rw

    sasang_axis: dict[str, Any] | None = None
    sd = _read_json(args.sasang_lens)
    if isinstance(sd, dict):
        raw_ax = sd.get("b_track_axis_scores_v1")
        if isinstance(raw_ax, dict) and str(raw_ax.get("schema")) == "sasang_b_track_axis_scores_v1":
            sasang_axis = raw_ax

    music_pt = _lens_music_gate_chain_passthrough(
        args.lens_music_gate_chain_json,
        enabled=not args.no_lens_music,
    )

    payload = {
        "schema": "cross_lens_rag_fusion_v1",
        "version": "1.1.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "non_gating": True,
        "logos_index_rows": logos_index_rows,
        "themes": themes,
        "lens_snapshots": lens_snapshots,
        "sasang_b_track_axis_scores_v1": sasang_axis,
        "lens_music_symbolic_passthrough_v1": music_pt,
        "cross_lens_conflict_matrix": conflict,
        "final_gate_panel": _build_final_gate(conflict, fusion_stub),
        "delta_from_prev": {
            "has_prev": False,
            "prev_ts_utc": None,
            "agreement_rate_delta": 0.0,
            "bull_ratio_delta": 0.0,
            "bear_ratio_delta": 0.0,
            "veto_changed": False,
        },
        "signal_light": {
            "schema": "signal_light_v1",
            "status": "YELLOW",
            "agreement_rate": 0.0,
            "veto_force_hold": False,
            "agreement_rate_delta": 0.0,
            "bear_ratio_delta": 0.0,
            "note": "Bootstrapping: waiting for first stable cycle.",
        },
        "note": "Cross-lens retrieval dashboard for observation only; no A-track auto trigger.",
    }
    prev = _read_last_history_row(args.history_jsonl)
    if isinstance(prev, dict):
        prev_agree = _safe_float(prev.get("agreement_rate"))
        prev_bull = _safe_float(prev.get("bull_count"))
        prev_bear = _safe_float(prev.get("bear_count"))
        prev_neu = _safe_float(prev.get("neutral_count"))
        prev_total = max(1.0, prev_bull + prev_bear + prev_neu)
        prev_bull_ratio = prev_bull / prev_total
        prev_bear_ratio = prev_bear / prev_total
        prev_veto = bool(prev.get("veto_force_hold"))
        curr_veto = bool(payload["final_gate_panel"].get("veto_force_hold"))
        payload["delta_from_prev"] = {
            "has_prev": True,
            "prev_ts_utc": prev.get("ts_utc"),
            "agreement_rate_delta": round(float(conflict.get("agreement_rate", 0.0)) - prev_agree, 6),
            "bull_ratio_delta": round(curr_bull_ratio - prev_bull_ratio, 6),
            "bear_ratio_delta": round(curr_bear_ratio - prev_bear_ratio, 6),
            "veto_changed": prev_veto != curr_veto,
        }
    payload["signal_light"] = _build_signal_light(payload)
    if args.force_signal_light:
        sl = payload["signal_light"]
        if isinstance(sl, dict):
            sl["status"] = args.force_signal_light
            sl["forced"] = True
            prev_note = str(sl.get("note") or "")
            sl["note"] = f"(forced override) {prev_note}".strip()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(args.out_md, payload)
    alert_written = False
    if not args.skip_alert_emit:
        alert_written = _emit_alert_if_needed(
            payload,
            args.alert_json,
            args.alert_log_jsonl,
            always_emit=bool(args.always_emit_alert),
        )
    if not args.skip_history_append:
        _append_history(args.history_jsonl, payload)
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"WROTE: {args.out_md.resolve()}")
    if alert_written:
        print(f"ALERT: {args.alert_json.resolve()}")
        print(f"APPEND: {args.alert_log_jsonl.resolve()}")
    if not args.skip_history_append:
        print(f"APPEND: {args.history_jsonl.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

