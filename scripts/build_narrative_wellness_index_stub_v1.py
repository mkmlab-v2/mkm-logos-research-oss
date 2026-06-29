#!/usr/bin/env python3
"""Build LWI-inspired narrative wellness index stub from dose spans ([HYPO])."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOSE = ROOT / "docs/final/schemas/warmth_content_dose_v1.example.json"
DEFAULT_OUT = ROOT / "reports/narrative_wellness_index_stub_v1_latest.json"

ICF_WEIGHTS = {
    "b2": 0.4,
    "b7": 0.25,
    "d4": 0.2,
    "e3": 0.15,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_domain_scores(spans: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for span in spans:
        code = str(span.get("icf_stub_code") or "b2")
        sk = int(span.get("sentiment_sk", 0))
        buckets[code].append(sk)
    out: dict[str, float] = {}
    for code, values in buckets.items():
        out[code] = sum(values) / len(values) if values else 0.0
    return out


def compute_a_t(domain_scores: dict[str, float]) -> float:
    total_w = 0.0
    acc = 0.0
    for code, s_at in domain_scores.items():
        w = ICF_WEIGHTS.get(code, 0.1)
        acc += w * ((s_at + 1.0) / 2.0)
        total_w += w
    return acc / total_w if total_w else 0.5


def compute_q_t(self_report_scales: dict[str, float]) -> float:
    """Keys 0-10; higher = worse for pain/stress unless invert key set."""
    invert = {"pain_0_10", "stress_0_10", "anxiety_0_10"}
    if not self_report_scales:
        return 0.5
    parts: list[float] = []
    n = len(self_report_scales)
    for key, raw in self_report_scales.items():
        norm = float(raw) / 10.0
        if key in invert:
            norm = 1.0 - norm
        parts.append(norm)
    return sum(parts) / n


def build_index(
    *,
    spans: list[dict[str, Any]],
    self_report_scales: dict[str, float],
    beta: float,
    time_period_t: str,
) -> dict[str, Any]:
    domain_scores = compute_domain_scores(spans)
    a_t = compute_a_t(domain_scores)
    q_t = compute_q_t(self_report_scales)
    beta = max(0.0, min(1.0, float(beta)))
    index_t = 100.0 * (beta * a_t + (1.0 - beta) * q_t)

    return {
        "schema": "narrative_wellness_index_stub_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "time_period_t": time_period_t,
        "index_t": round(index_t, 4),
        "beta_mix": round(beta, 4),
        "components": {
            "a_t": round(a_t, 6),
            "q_t": round(q_t, 6),
            "domain_scores": {k: round(v, 6) for k, v in domain_scores.items()},
        },
        "external_citation_status": "pending",
        "provenance": {
            "source": "build_narrative_wellness_index_stub_v1",
            "experiment_id": "wtt_epb_pilot_01",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dose-json", type=Path, default=DEFAULT_DOSE)
    ap.add_argument("--beta", type=float, default=0.6)
    ap.add_argument("--pain-0-10", type=float, default=4.0)
    ap.add_argument("--stress-0-10", type=float, default=5.0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    dose = _load_json(args.dose_json)
    spans = list(dose.get("narrative_spans_stub") or [])
    self_report = {
        "pain_0_10": float(args.pain_0_10),
        "stress_0_10": float(args.stress_0_10),
    }
    report = build_index(
        spans=spans,
        self_report_scales=self_report,
        beta=args.beta,
        time_period_t=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "index_t": report["index_t"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
