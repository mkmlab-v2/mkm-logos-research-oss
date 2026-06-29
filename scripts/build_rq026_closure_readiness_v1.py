#!/usr/bin/env python3
"""RQ-026 B-track closure readiness gate ([HYPO]) — does not set CLOSED."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq026_closure_readiness_v1_latest.json"

CHECKS: list[tuple[str, Path, str]] = [
    ("signoff", ROOT / "docs/final/artifacts/rq026_commander_btrack_signoff_v1_latest.json", "schema"),
    ("phase2_eval", ROOT / "docs/final/artifacts/sasang_temperament_agents_phase2_eval_v1_latest.json", "eval_separation_ok"),
    ("phase4", ROOT / "docs/final/artifacts/sasang_temperament_agents_phase4_holdout_ablation_v1_latest.json", "holdout_gates"),
    ("narrative_lint", ROOT / "docs/final/artifacts/rq026_narrative_lint_v1_latest.json", "narrative_lint_ok"),
    ("matrix_promotion_v1_2", ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_2_btrack_promotion_v1_latest.json", "promoted_matrix_version"),
    ("matrix_sweep", ROOT / "docs/final/artifacts/sasang_temperament_agents_matrix_sweep_v1_latest.json", "recommended_candidate"),
    ("sim_report", ROOT / "reports/sasang_temperament_agents_sim_v1_latest.json", "not_promoted_track_a"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    mechanics_ok = True
    for name, path, key in CHECKS:
        doc = _load(path)
        ok = doc is not None
        detail: Any = None
        if doc is not None:
            if key == "eval_separation_ok":
                ok = doc.get(key) is True
                detail = doc.get(key)
            elif key == "narrative_lint_ok":
                ok = doc.get(key) is True
                detail = doc.get(key)
            elif key == "holdout_gates":
                gates = doc.get(key) or {}
                ok = gates.get("both_pass") is True
                detail = gates
            elif key == "recommended_candidate":
                rec = doc.get(key) or {}
                ok = rec.get("variant") == "v1_2"
                detail = rec
            elif key == "promoted_matrix_version":
                ok = doc.get(key) == "1.2.0"
                detail = doc.get(key)
            elif key == "not_promoted_track_a":
                ok = doc.get(key) is True
                detail = doc.get(key)
            else:
                detail = doc.get(key)
        if not ok:
            mechanics_ok = False
        rows.append(
            {
                "check": name,
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "ok": ok,
                "detail": detail,
            }
        )

    blockers = [
        "McNemar p≈0.47 on price AB — not promotion proof for temperament sim.",
        "Temperament sim is mechanics/research_only — not clinical or Track A evidence.",
    ]
    close_path = ROOT / "docs/final/artifacts/rq026_commander_close_v1_latest.json"
    close_doc = _load(close_path)
    closure_allowed = close_doc is not None and close_doc.get("rq_026_closed") is True
    if not closure_allowed:
        blockers.insert(
            0,
            "RQ-026 CLOSED requires commander close artifact (record_rq026_commander_close_v1.py).",
        )

    return {
        "schema": "rq026_closure_readiness_v1",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-026",
        "hypothesis_tier": "B",
        "research_only": True,
        "mechanics_bundle_ok": mechanics_ok,
        "closure_allowed": closure_allowed,
        "checks": rows,
        "blockers_ko": blockers,
        "next_human_gate": (
            ["None — RQ-026 CLOSED; reopen only via new RQ id."]
            if closure_allowed
            else [
                "Commander sign-off to mark RQ-026 CLOSED in RESEARCH_OPEN_QUESTIONS_V1.md",
                "Run record_rq026_commander_close_v1.py after mechanics bundle OK",
            ]
        ),
        "verdict_ko": (
            "RQ-026 CLOSED 이관 OK — commander close 기록됨."
            if closure_allowed and mechanics_ok
            else (
                "B-track mechanics 번들 OK — commander close 대기."
                if mechanics_ok
                else "mechanics 번들 일부 누락/실패 — chain 재실행 필요."
            )
        ),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="exit 1 if mechanics_bundle_ok false")
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    if args.strict and not doc.get("mechanics_bundle_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
