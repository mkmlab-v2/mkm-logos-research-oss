#!/usr/bin/env python3
"""KSSDS vs semantic_chunk decision + optional alignment spike summary [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_alignment_routing_lib_v1 import (  # noqa: E402
    BACKEND_FASTER_WHISPER,
    BACKEND_WHISPERX,
    MODE_AUTO,
    alignment_routing_contract_v1,
    build_alignment_routing_table_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_segment_backend_decision_v1_latest.json"
KSSDS_BENCH = ROOT / "reports/ko_shorts_segment_backend_bench_kssds_v1_latest.json"
BASE_BENCH = ROOT / "reports/ko_shorts_segment_backend_bench_v1_latest.json"
ALIGN_SPIKE = ROOT / "reports/ko_shorts_alignment_backend_spike_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _summarize_segment_bench(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"available": False}
    deltas = []
    for case in doc.get("cases") or []:
        cid = case.get("case_id")
        delta = case.get("delta_kss_minus_semantic_line_count")
        if delta is not None:
            deltas.append({"case_id": cid, "delta": delta})
    return {
        "available": True,
        "kssds_status": doc.get("kssds_status"),
        "case_count": len(doc.get("cases") or []),
        "semantic_vs_kss_line_delta": deltas,
    }


def _summarize_alignment(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"available": False}
    rows = []
    for case in doc.get("cases") or []:
        cid = case.get("case_id")
        applied = (case.get("alignment_routing_applied") or {}).get("applied_backend")
        routed = case.get("routed_backend") or {}
        if case.get("backends"):
            fw = ((case.get("backends") or {}).get("faster_whisper_word_ts") or {})
            st = ((case.get("backends") or {}).get("stable_ts") or {})
            wx = ((case.get("backends") or {}).get("whisperx") or {})
            rows.append(
                {
                    "case_id": cid,
                    "mode": "bench_all",
                    "faster_whisper_start_drift_ms": (fw.get("drift_vs_proportional") or {}).get(
                        "start_drift_ms_mean"
                    ),
                    "stable_ts_start_drift_ms": (st.get("drift_vs_proportional") or {}).get("start_drift_ms_mean")
                    if st.get("ok")
                    else None,
                    "whisperx_start_drift_ms": (wx.get("drift_vs_proportional") or {}).get("start_drift_ms_mean")
                    if wx.get("ok")
                    else None,
                    "delta_vs_faster_whisper": case.get("delta_vs_faster_whisper"),
                }
            )
        else:
            rows.append(
                {
                    "case_id": cid,
                    "mode": doc.get("alignment_backend_mode") or "routed",
                    "applied_backend": applied,
                    "routing_rule_id": (case.get("routing") or {}).get("rule_id"),
                    "start_drift_ms_mean": (routed.get("drift_vs_proportional") or {}).get("start_drift_ms_mean"),
                    "routing_fallback": (case.get("alignment_routing_applied") or {}).get("routing_fallback"),
                }
            )
    return {
        "available": True,
        "alignment_backend_mode": doc.get("alignment_backend_mode"),
        "backend_status": doc.get("backend_status"),
        "cases": rows,
    }


def _routing_recommendation_v1(align: dict[str, Any] | None) -> dict[str, Any]:
    contract = alignment_routing_contract_v1()
    default_cases = ["web_pansori", "web_deeply", "web_youtube_edu"]
    table = build_alignment_routing_table_v1(default_cases, mode=MODE_AUTO)
    rec = {
        "alignment_mode_default": MODE_AUTO,
        "per_case_auto": table,
        "pansori_backend": BACKEND_WHISPERX,
        "non_pansori_backend": BACKEND_FASTER_WHISPER,
        "whisperx_adopt_default": False,
        "whisperx_scope": "web_pansori / domain_hint traditional_vocal only",
        "stable_ts_scope": "bench_all research only — not default route",
    }
    if align:
        pansori = next((c for c in align.get("cases") or [] if c.get("case_id") == "web_pansori"), None)
        if pansori and pansori.get("backends"):
            wx = ((pansori.get("backends") or {}).get("whisperx") or {})
            fw = ((pansori.get("backends") or {}).get("faster_whisper_word_ts") or {})
            wx_d = float((wx.get("drift_vs_proportional") or {}).get("start_drift_ms_mean") or 0.0)
            fw_d = float((fw.get("drift_vs_proportional") or {}).get("start_drift_ms_mean") or 0.0)
            if wx.get("ok") and wx_d < fw_d - 500:
                rec["whisperx_pansori_delta_ms"] = round(wx_d - fw_d, 2)
                rec["whisperx_adopt_default"] = False
                rec["whisperx_scope"] = "auto-route pansori only — bench evidence supports selective use"
    contract["recommendation"] = rec
    return contract


def build_decision_report_v1(*, alignment_path: Path | None = None) -> dict[str, Any]:
    kssds = _read_json(KSSDS_BENCH)
    base = _read_json(BASE_BENCH)
    align_path = alignment_path or ALIGN_SPIKE
    align = _read_json(align_path) if align_path else None

    segment_default = "semantic_chunk_ko_v1"
    segment_optional = ["kss_fast", "kssds"]
    alignment_default = "auto routing — faster_whisper_word_ts default; whisperx for pansori/traditional_vocal"
    alignment_candidate = "bench_all stable_ts/whisperx comparison — research only"

    recommendation = {
        "segment_default_backend": segment_default,
        "segment_optional_backends": segment_optional,
        "kssds_adopt_default": False,
        "kssds_reason": (
            "KSSDS matches semantic on real corpora line_count; requires isolated venv "
            "(transformers==4.42.4) and GPU latency — keep optional bench path only."
        ),
        "alignment_default": alignment_default,
        "alignment_backend_cli": "--alignment-backend auto",
        "alignment_next_experiment": alignment_candidate,
        "track_a_promotion": "blocked",
        "send_gate": "HOLD",
    }

    routing = _routing_recommendation_v1(align)
    recommendation["alignment_routing_summary"] = routing.get("recommendation")

    if align and (align.get("backend_status") or {}).get("stable_ts") == "ok":
        pansori = next((c for c in align.get("cases") or [] if c.get("case_id") == "web_pansori"), None)
        if pansori:
            deltas = pansori.get("delta_vs_faster_whisper") or []
            if deltas:
                d0 = deltas[0]
                recommendation["stable_ts_pansori_delta_ms"] = d0.get("delta_minus_faster_whisper_ms")
                if float(d0.get("delta_minus_faster_whisper_ms") or 0.0) < -500.0:
                    recommendation["alignment_next_experiment"] = (
                        "stable_ts shows lower P0-P1 gap on pansori — continue B-track eval only"
                    )

    return {
        "schema": "ko_shorts_segment_backend_decision_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "segment_bench_kssds": _summarize_segment_bench(kssds or base),
        "alignment_spike": _summarize_alignment(align),
        "alignment_routing": routing,
        "recommendation": recommendation,
        "reproduce": "py scripts/build_ko_shorts_segment_backend_decision_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--alignment-spike", type=Path, default=None)
    args = ap.parse_args()

    align = args.alignment_spike if args.alignment_spike and args.alignment_spike.is_absolute() else (
        (ROOT / args.alignment_spike) if args.alignment_spike else None
    )
    report = build_decision_report_v1(alignment_path=align)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
