#!/usr/bin/env python3
"""Render cross-lens RAG fusion JSON into a standalone HTML dashboard."""
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_fusion_latest.json"
DEFAULT_OUTPUT = ROOT / "reports" / "cross_lens_rag_fusion_dashboard_latest.html"
DEFAULT_HISTORY = ROOT / "reports" / "cross_lens_rag_fusion_history.jsonl"


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Input JSON must be an object.")
    return obj


def _read_history(path: Path, tail: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    if tail > 0:
        rows = rows[-tail:]
    return rows


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{escape(text)}</span>'


def _sign_cls(sign: str) -> str:
    return {
        "bull": "bull",
        "bear": "bear",
        "neutral": "neutral",
    }.get(sign, "neutral")


def _render(payload: dict[str, Any], history: list[dict[str, Any]]) -> str:
    ts = str(payload.get("ts_utc", "unknown"))
    index_rows = payload.get("logos_index_rows", "unknown")
    themes = payload.get("themes") if isinstance(payload.get("themes"), list) else []
    lenses = payload.get("lens_snapshots") if isinstance(payload.get("lens_snapshots"), list) else []
    matrix = payload.get("cross_lens_conflict_matrix") if isinstance(payload.get("cross_lens_conflict_matrix"), dict) else {}
    gate = payload.get("final_gate_panel") if isinstance(payload.get("final_gate_panel"), dict) else {}
    delta = payload.get("delta_from_prev") if isinstance(payload.get("delta_from_prev"), dict) else {}
    signal = payload.get("signal_light") if isinstance(payload.get("signal_light"), dict) else {}

    lens_rows_html: list[str] = []
    for row in lenses:
        if not isinstance(row, dict):
            continue
        sign = str(row.get("direction_sign", "neutral"))
        lens_rows_html.append(
            "<tr>"
            f"<td>{escape(str(row.get('lens_id', '?')))}</td>"
            f"<td>{_badge(sign.upper(), _sign_cls(sign))}</td>"
            f"<td>{float(row.get('direction_score', 0.0)):.6f}</td>"
            f"<td>{float(row.get('confidence', 0.0)):.6f}</td>"
            f"<td>{escape(str(row.get('artifact_ts_utc', '-')))}</td>"
            "</tr>"
        )

    theme_rows_html: list[str] = []
    for row in themes:
        if not isinstance(row, dict):
            continue
        anchors = row.get("top_verse_ids") if isinstance(row.get("top_verse_ids"), list) else []
        anchor_txt = ", ".join(str(x) for x in anchors)
        theme_rows_html.append(
            "<tr>"
            f"<td>{escape(str(row.get('theme', '?')))}</td>"
            f"<td>{int(row.get('top_count', 0))}</td>"
            f"<td>{float(row.get('avg_score_top5', 0.0)):.6f}</td>"
            f"<td>{escape(anchor_txt)}</td>"
            "</tr>"
        )

    sign_counts = matrix.get("sign_counts") if isinstance(matrix.get("sign_counts"), dict) else {}
    bull_count = int(sign_counts.get("bull", 0))
    bear_count = int(sign_counts.get("bear", 0))
    neutral_count = int(sign_counts.get("neutral", 0))
    agreement = float(matrix.get("agreement_rate", 0.0))
    majority_sign = str(matrix.get("majority_sign", "neutral"))
    veto = bool(gate.get("veto_force_hold", False))
    veto_reasons = gate.get("veto_reason_codes") if isinstance(gate.get("veto_reason_codes"), list) else []
    veto_txt = ", ".join(str(x) for x in veto_reasons) if veto_reasons else "none"
    has_prev = bool(delta.get("has_prev"))
    prev_ts = str(delta.get("prev_ts_utc") or "-")
    d_agree = float(delta.get("agreement_rate_delta", 0.0))
    d_bull = float(delta.get("bull_ratio_delta", 0.0))
    d_bear = float(delta.get("bear_ratio_delta", 0.0))
    d_veto = bool(delta.get("veto_changed", False))
    light = str(signal.get("status", "YELLOW")).upper()
    light_note = str(signal.get("note", ""))
    light_cls = "ok" if light == "GREEN" else ("warn" if light == "YELLOW" else "warn")

    def _fmt_delta(v: float) -> str:
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.6f}"

    hist_points: list[tuple[str, float, bool, float, float]] = []
    for row in history:
        ts_label = str(row.get("ts_utc", ""))[-8:] if row.get("ts_utc") else "?"
        ar = float(row.get("agreement_rate", 0.0))
        vh = bool(row.get("veto_force_hold", False))
        bull = float(row.get("bull_count", 0.0))
        bear = float(row.get("bear_count", 0.0))
        neu = float(row.get("neutral_count", 0.0))
        total = max(1.0, bull + bear + neu)
        hist_points.append((ts_label, max(0.0, min(1.0, ar)), vh, bull / total, bear / total))
    if not hist_points:
        hist_points.append(("n/a", agreement, veto, 0.0, 0.0))
    reason_counts: dict[str, int] = {}
    for row in history:
        codes = row.get("veto_reason_codes") if isinstance(row, dict) else None
        if not isinstance(codes, list):
            continue
        for code in codes:
            key = str(code)
            reason_counts[key] = reason_counts.get(key, 0) + 1
    point_width = 100.0 / max(1, len(hist_points) - 1)
    agree_pts: list[str] = []
    bull_pts: list[str] = []
    bear_pts: list[str] = []
    for i, (_, ar, _, bull_ratio, bear_ratio) in enumerate(hist_points):
        x = i * point_width
        y_agree = 90.0 - (ar * 80.0)
        y_bull = 90.0 - (bull_ratio * 80.0)
        y_bear = 90.0 - (bear_ratio * 80.0)
        agree_pts.append(f"{x:.2f},{y_agree:.2f}")
        bull_pts.append(f"{x:.2f},{y_bull:.2f}")
        bear_pts.append(f"{x:.2f},{y_bear:.2f}")
    polyline_agree = " ".join(agree_pts)
    polyline_bull = " ".join(bull_pts)
    polyline_bear = " ".join(bear_pts)
    dots: list[str] = []
    labels: list[str] = []
    for i, (label, ar, vh, _, _) in enumerate(hist_points):
        x = i * point_width
        y = 90.0 - (ar * 80.0)
        color = "#b91c1c" if vh else "#1d4ed8"
        dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.4" fill="{color}" />')
        if i == 0 or i == len(hist_points) - 1 or i % max(1, len(hist_points)//6) == 0:
            labels.append(f'<text x="{x:.2f}" y="108" text-anchor="middle" font-size="9" fill="#666">{escape(label)}</text>')

    reason_rows: list[str] = []
    if reason_counts:
        for reason, cnt in sorted(reason_counts.items(), key=lambda x: (-x[1], x[0])):
            reason_rows.append(f"<tr><td>{escape(reason)}</td><td>{cnt}</td></tr>")
    else:
        reason_rows.append("<tr><td>none</td><td>0</td></tr>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cross-Lens RAG Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; color: #111; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: #fafafa; }}
    h1, h2 {{ margin: 0 0 10px 0; }}
    h2 {{ margin-top: 20px; }}
    .meta {{ color: #666; margin-bottom: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border: 1px solid #e2e2e2; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ background: #f2f2f2; }}
    .badge {{ padding: 3px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }}
    .bull {{ background: #d1fae5; color: #065f46; }}
    .bear {{ background: #fee2e2; color: #991b1b; }}
    .neutral {{ background: #e5e7eb; color: #374151; }}
    .warn {{ color: #7c2d12; font-weight: 700; }}
    .ok {{ color: #065f46; font-weight: 700; }}
    .bar {{ height: 14px; background: #f3f4f6; border-radius: 99px; overflow: hidden; }}
    .bar > span {{ display: block; height: 14px; background: #2563eb; width: {max(0.0, min(1.0, agreement))*100:.2f}%; }}
    .chart-wrap {{ border: 1px solid #ddd; border-radius: 8px; padding: 8px; background: #fff; }}
    .legend {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 2px 0; font-size: 12px; color: #444; }}
    .legend i {{ display: inline-block; width: 14px; height: 3px; vertical-align: middle; margin-right: 6px; border-radius: 2px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Cross-Lens RAG Fusion Dashboard</h1>
    <div class="meta">generated_at_utc: {escape(ts)} | logos_index_rows: {escape(str(index_rows))}</div>

    <div class="cards">
      <div class="card"><strong>Majority Sign</strong><br>{_badge(majority_sign.upper(), _sign_cls(majority_sign))}</div>
      <div class="card"><strong>Agreement Rate</strong><br>{agreement:.6f}</div>
      <div class="card"><strong>Bull/Bear/Neutral</strong><br>{bull_count} / {bear_count} / {neutral_count}</div>
      <div class="card"><strong>Gate</strong><br><span class="{'warn' if veto else 'ok'}">{'VETO_HOLD' if veto else 'PASS'}</span></div>
    </div>
    <div class="meta"><strong>Signal Light:</strong> <span class="{light_cls}">{escape(light)}</span> — {escape(light_note)}</div>

    <h2>Conflict Matrix</h2>
    <div class="bar"><span></span></div>
    <div class="meta">veto_reason_codes: {escape(veto_txt)}</div>

    <h2>Delta From Previous Snapshot</h2>
    <table>
      <thead>
        <tr><th>Field</th><th>Delta</th><th>Previous TS</th></tr>
      </thead>
      <tbody>
        <tr><td>agreement_rate</td><td>{_fmt_delta(d_agree)}</td><td>{escape(prev_ts) if has_prev else '-'}</td></tr>
        <tr><td>bull_ratio</td><td>{_fmt_delta(d_bull)}</td><td>{escape(prev_ts) if has_prev else '-'}</td></tr>
        <tr><td>bear_ratio</td><td>{_fmt_delta(d_bear)}</td><td>{escape(prev_ts) if has_prev else '-'}</td></tr>
        <tr><td>veto_changed</td><td>{'true' if d_veto else 'false'}</td><td>{escape(prev_ts) if has_prev else '-'}</td></tr>
      </tbody>
    </table>

    <h2>Agreement Timeline</h2>
    <div class="chart-wrap">
      <div class="legend">
        <span><i style="background:#2563eb"></i>Agreement Rate</span>
        <span><i style="background:#059669"></i>Bull Ratio</span>
        <span><i style="background:#dc2626"></i>Bear Ratio</span>
      </div>
      <svg viewBox="0 0 100 112" width="100%" height="180" role="img" aria-label="Agreement timeline">
        <line x1="0" y1="90" x2="100" y2="90" stroke="#d1d5db" stroke-width="0.8" />
        <line x1="0" y1="10" x2="0" y2="90" stroke="#d1d5db" stroke-width="0.8" />
        <text x="2" y="12" font-size="9" fill="#666">1.0</text>
        <text x="2" y="92" font-size="9" fill="#666">0.0</text>
        <polyline fill="none" stroke="#059669" stroke-width="1.0" stroke-dasharray="2 1" points="{polyline_bull}" />
        <polyline fill="none" stroke="#dc2626" stroke-width="1.0" stroke-dasharray="2 1" points="{polyline_bear}" />
        <polyline fill="none" stroke="#2563eb" stroke-width="1.3" points="{polyline_agree}" />
        {''.join(dots)}
        {''.join(labels)}
      </svg>
      <div class="meta">Blue dot: pass, Red dot: veto hold. Tail points: {len(hist_points)}</div>
    </div>

    <h2>Lens Evidence Map</h2>
    <table>
      <thead>
        <tr><th>Lens</th><th>Sign</th><th>Direction Score</th><th>Confidence</th><th>Artifact TS</th></tr>
      </thead>
      <tbody>
        {''.join(lens_rows_html)}
      </tbody>
    </table>

    <h2>Theme Retrieval Summary</h2>
    <table>
      <thead>
        <tr><th>Theme</th><th>Top-K Count</th><th>Avg Score Top5</th><th>Top Anchors</th></tr>
      </thead>
      <tbody>
        {''.join(theme_rows_html)}
      </tbody>
    </table>

    <h2>Veto Reason Frequency (Tail Window)</h2>
    <table>
      <thead>
        <tr><th>Reason Code</th><th>Count</th></tr>
      </thead>
      <tbody>
        {''.join(reason_rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Render cross-lens RAG fusion JSON as HTML.")
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-html", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--history-tail", type=int, default=30)
    args = ap.parse_args()

    payload = _read_json(args.input_json)
    history = _read_history(args.history_jsonl, max(1, args.history_tail))
    html = _render(payload, history)
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")
    print(f"WROTE: {args.output_html.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

