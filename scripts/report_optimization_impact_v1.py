#!/usr/bin/env python3
"""Build shadow-safe optimization impact report from compression perf test v1."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PERF_DEFAULT = ROOT / "reports/compression_perf_test_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/optimization_impact_v1_latest.json"
OUT_MD_DEFAULT = ROOT / "reports/optimization_impact_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _md(doc: dict[str, Any]) -> str:
    raw = (doc.get("raw") or {})
    sh = (doc.get("shadow") or {})
    d = doc.get("delta_shadow_minus_raw") or {}
    lines = [
        "# Optimization Impact v1 (Shadow)",
        "",
        f"- generated: `{doc.get('generated_at_utc')}`",
        "- lane: `research_only` · `non_gating`",
        "- note: Track A production policy unchanged",
        "",
        "## Raw vs Shadow",
        "",
        "| metric | raw | shadow | delta(shadow-raw) |",
        "|---|---:|---:|---:|",
        f"| global_token_saving_rate | {raw.get('global_token_saving_rate')} | {sh.get('global_token_saving_rate')} | {d.get('global_token_saving_rate')} |",
        f"| avg_reconstruction_fidelity_jaccard | {raw.get('avg_reconstruction_fidelity_jaccard')} | {sh.get('avg_reconstruction_fidelity_jaccard')} | {d.get('avg_reconstruction_fidelity_jaccard')} |",
        f"| avg_sensitive_integrity | {raw.get('avg_sensitive_integrity')} | {sh.get('avg_sensitive_integrity')} | {d.get('avg_sensitive_integrity')} |",
        "",
        "## Guard",
        "",
        "- `track_a_bridge: false`",
        "- `live_trading_bridge: false`",
        "- `production_policy_unchanged: true`",
        "",
    ]
    return "\n".join(lines) + "\n"


def build(perf_doc: dict[str, Any]) -> dict[str, Any]:
    raw = ((perf_doc.get("raw_baseline") or {}).get("metrics") or {})
    shadow = ((perf_doc.get("logic_aware_shadow") or {}).get("metrics") or {})
    delta = perf_doc.get("delta_shadow_minus_raw") or {}
    return {
        "schema": "optimization_impact_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "production_policy_unchanged": True,
            "headline_claim_forbidden_without_tracka_gate": True,
        },
        "source_perf_report": "reports/compression_perf_test_v1_latest.json",
        "raw": raw,
        "shadow": shadow,
        "delta_shadow_minus_raw": delta,
        "logic_aware_terms_count": perf_doc.get("logic_aware_terms_count"),
        "interpretation_guard": (
            "Shadow deltas are research signals only; do not mutate Track A routing, "
            "must_keep policy, or external claims without separate gate approval."
        ),
        "reproduce": "py scripts/report_optimization_impact_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--perf", type=Path, default=PERF_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--out-md", type=Path, default=OUT_MD_DEFAULT)
    args = ap.parse_args()

    perf_doc = _load(args.perf)
    if not perf_doc:
        print(json.dumps({"ok": False, "error": "missing perf report"}))
        return 2
    doc = build(perf_doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_md(doc), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "delta": doc.get("delta_shadow_minus_raw"),
                "out": str(args.out),
                "out_md": str(args.out_md),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
