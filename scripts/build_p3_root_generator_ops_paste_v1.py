#!/usr/bin/env python3
"""Build commander ops paste for P3 Root Generator weekly (B-track)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_MD = ROOT / "reports/p3_root_generator_ops_paste_v1_latest.md"
OUT_JSON = ROOT / "reports/p3_root_generator_ops_paste_v1_latest.json"
BUILD_REPORT = ROOT / "reports/p3_root_candidate_lexicon_build_v1_latest.json"
BENCH_REPORT = ROOT / "reports/p3_root_generator_bench_v1_latest.json"
GATE_REPORT = ROOT / "reports/p3_root_generator_bench_gate_v1_latest.json"
SHALLOW_SLICE = ROOT / "reports/p3_root_shallow_router_slice_v1_latest.json"
WEEKLY_REPORT = ROOT / "reports/p3_root_generator_weekly_v1_latest.json"
NSM_REPORT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    build = _read(BUILD_REPORT) or {}
    bench = _read(BENCH_REPORT) or {}
    gate = _read(GATE_REPORT) or {}
    shallow = _read(SHALLOW_SLICE) or {}
    weekly = _read(WEEKLY_REPORT) or {}
    nsm = _read(NSM_REPORT) or {}
    nsm_base = nsm.get("baseline") or {}

    cmp_ = bench.get("comparison") or {}
    lines = [
        "# P3 Root Generator — weekly ops paste",
        "",
        f"- generated_at_utc: `{_utc()}`",
        f"- track: B-track · research_only · send_gate: HOLD",
        "",
        "## Extension chain",
        f"- build candidate: `{build.get('candidate_path', 'missing')}`",
        f"- rows: baseline `{build.get('baseline_row_count', '?')}` → candidate `{build.get('candidate_row_count', '?')}` (+{build.get('rows_added', '?')})",
        f"- bench profile: `{bench.get('profile', '?')}`",
        f"- oov_delta: `{cmp_.get('oov_hit_ratio_delta', '?')}`",
        f"- router_lexicon_delta: `{cmp_.get('router_probe_lexicon_hit_rate_delta', '?')}`",
        f"- gate decision: `{gate.get('decision', '?')}` ({', '.join(gate.get('reasons') or [])})",
        "",
        "## Replacement (logos seed research)",
        f"- weekly status: `{weekly.get('replacement', {}).get('status', 'n/a')}`",
        f"- candidate rows: `{weekly.get('replacement', {}).get('candidate_row_count', 'n/a')}`",
        "",
        "## Shallow router slice",
        f"- mode: `{shallow.get('status', weekly.get('shallow_router', {}).get('status', 'n/a'))}`",
        f"- router_hit_rate: `{shallow.get('router_hit_rate', 'n/a')}`",
        "",
        "## NSM 100-pair crosswalk (B-track)",
        f"- prime_hit_rate: `{nsm_base.get('prime_hit_rate', 'n/a')}`",
        f"- english_only_distortion_rate: `{nsm_base.get('english_only_distortion_rate', 'n/a')}`",
        f"- aligned_original_language: `{nsm_base.get('aligned_original_language_count', 'n/a')}`",
        f"- research_verdict: corpus-anchor ≠ NSM universal root",
        "",
        "## Hangul 41676 (Design lane · promotion HOLD)",
        f"- decision: `{weekly.get('hangul41676', {}).get('decision', 'n/a')}`",
        f"- promotion: `{weekly.get('hangul41676', {}).get('promotion', 'HOLD')}`",
        "",
        "## Repro",
        "```powershell",
        "py scripts/run_p3_root_generator_weekly_v1.py",
        "powershell -File scripts\\Register-P3RootGeneratorWeeklyTask_v1.ps1",
        "```",
    ]

    payload = {
        "schema": "p3_root_generator_ops_paste_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "build": build,
        "bench": {
            "profile": bench.get("profile"),
            "comparison": cmp_,
        },
        "gate": {
            "decision": gate.get("decision"),
            "reasons": gate.get("reasons"),
        },
        "shallow_router_slice": shallow,
        "weekly": weekly,
        "nsm_crosswalk": {
            "prime_hit_rate": nsm_base.get("prime_hit_rate"),
            "distortion_rate": nsm_base.get("english_only_distortion_rate"),
            "gate_ok": (nsm.get("gates") or {}).get("gate_ok"),
        },
    }

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote_md": str(OUT_MD), "wrote_json": str(OUT_JSON)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
