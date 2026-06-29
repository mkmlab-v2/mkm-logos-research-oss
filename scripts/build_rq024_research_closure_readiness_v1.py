#!/usr/bin/env python3
"""RQ-024 B-track research closure readiness — mechanics gate; does not set CLOSED."""
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

DEFAULT_OUT = ROOT / "docs/final/artifacts/rq024_research_closure_readiness_v1_latest.json"
COMMANDER_CLOSE = ROOT / "docs/final/artifacts/rq024_commander_research_close_v1_latest.json"
SCHEMA = "rq024_research_closure_readiness_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def build() -> dict[str, Any]:
    checks_spec: list[tuple[str, Path, str]] = [
        ("triangle_v1", ROOT / "reports/rq024_btc_lens_v1_triangular_validation_v1_latest.json", "triangle.met"),
        ("holdout_v1", ROOT / "reports/rq024_btc_lens_feature_v0_blind_holdout_v1_latest.json", "dod_v1.met"),
        ("multisplit_v1", ROOT / "reports/rq024_btc_lens_feature_v0_multisplit_v1_latest.json", "dod_multisplit_v1.met"),
        ("wf_ablation_v1", ROOT / "reports/rq024_btc_lens_feature_v0_wf_ablation_v1_latest.json", "dod_wf_ablation.best_v1_mean_beats_052"),
        ("nf5_replication", ROOT / "reports/rq024_btc_lens_v1_nf5_wf_replication_v1_latest.json", "dod_nf5_replication.met"),
        ("wf_stability", ROOT / "reports/rq024_btc_lens_v1_wf_stability_v1_latest.json", "best_v1_nf"),
        ("flow_charter", ROOT / "docs/final/artifacts/rq024_kospi_flow_proxy_sublane_a_v1.json", "score_path_sidecar"),
        ("chain_bundle", ROOT / "reports/rq024_btc_lens_feature_v0_chain_v1_latest.json", "chain_ok"),
    ]

    rows: list[dict[str, Any]] = []
    mechanics_ok = True
    for name, path, key in checks_spec:
        doc = _load(path)
        ok = doc is not None
        detail: Any = None
        if doc is not None:
            if key == "triangle.met":
                ok = (doc.get("triangle") or {}).get("met") is True
                detail = doc.get("triangle")
            elif key == "dod_v1.met":
                ok = (doc.get("dod_v1") or {}).get("met") is True
                detail = doc.get("dod_v1")
            elif key == "dod_multisplit_v1.met":
                ok = (doc.get("dod_multisplit_v1") or {}).get("met") is True
                detail = doc.get("dod_multisplit_v1")
            elif key == "dod_wf_ablation.best_v1_mean_beats_052":
                ok = (doc.get("dod_wf_ablation") or {}).get("best_v1_mean_beats_052") is True
                detail = doc.get("dod_wf_ablation")
            elif key == "dod_nf5_replication.met":
                ok = (doc.get("dod_nf5_replication") or {}).get("met") is True
                detail = doc.get("dod_nf5_replication")
            elif key == "best_v1_nf":
                ok = doc.get(key) == 5
                detail = {"best_v1_nf": doc.get(key), "weak_nf": doc.get("weak_nf_configs")}
            elif key == "score_path_sidecar":
                ok = isinstance(doc.get(key), dict) and doc[key].get("merge_into_btc_lens_promotion") is False
                detail = {"gating": doc.get("gating")}
            elif key == "chain_ok":
                ok = doc.get(key) is True
                detail = doc.get("final_action")
            else:
                detail = doc.get(key)
        if not ok:
            mechanics_ok = False
        rows.append({"check": name, "path": _rel(path), "ok": ok, "detail": detail})

    close_doc = _load(COMMANDER_CLOSE)
    commander_closed = close_doc is not None and close_doc.get("rq_024_research_closed") is True
    closure_allowed = commander_closed and mechanics_ok

    triangle = _load(ROOT / "reports/rq024_btc_lens_v1_triangular_validation_v1_latest.json") or {}
    nf5 = _load(ROOT / "reports/rq024_btc_lens_v1_nf5_wf_replication_v1_latest.json") or {}

    blockers: list[str] = []
    if not mechanics_ok:
        blockers.append("Mechanics bundle incomplete — re-run post-triangle chain.")
    if not commander_closed:
        blockers.append("Commander research-close artifact missing (human gate).")
    blockers.extend(
        [
            "Gate 0.55 not met — not a promotion success claim.",
            "nf6/nf7 WF sensitivity remains — pin nf=5 for replication only.",
            "Track A / live trading auto-merge forbidden.",
            "KOSPI flow [NON_GATING] must not enter BTC lens verdict.",
        ]
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "rq_id": "RQ-024",
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "mechanics_bundle_ok": mechanics_ok,
        "closure_allowed": closure_allowed,
        "commander_close_on_disk": commander_closed,
        "checks": rows,
        "headline_metrics": {
            "v1_triangle_met": (triangle.get("triangle") or {}).get("met"),
            "v1_holdout_accuracy": (triangle.get("legs") or {}).get("single_50_50_holdout", {}).get("accuracy"),
            "v1_multisplit_mean": (triangle.get("legs") or {}).get("multisplit_chronological", {}).get("mean_accuracy"),
            "v1_nf5_wf_mean": (nf5.get("v1_aggregate") or {}).get("mean_test_accuracy"),
            "gate_055_promotion": False,
            "track_a_status": "blocked",
        },
        "blockers_ko": blockers,
        "next_human_gate": (
            ["None — RQ-024 research CLOSED on disk."]
            if closure_allowed
            else [
                "지휘관: triangle + nf5 replication 검토 후 record_rq024_commander_research_close_v1.py 실행",
                "RESEARCH_OPEN_QUESTIONS_V1.md RQ-024 행을 CLOSED(T1 research)로 수동 갱신",
            ]
        ),
        "verdict_ko": (
            "RQ-024 B-track research CLOSED 이관 OK."
            if closure_allowed
            else (
                "Mechanics 번들 OK — commander research-close 대기 (Track A 승격 아님)."
                if mechanics_ok
                else "Mechanics 번들 일부 누락 — post-triangle chain 재실행."
            )
        ),
        "messaging_contract": {
            "allowed": [
                "v1 triangular validation 3/3 on promotion-legal axis (no expanded-prior)",
                "nf5 pinned blocked-WF replication as recommended research config",
                "raw remains primary; repair_v2 is operational evidence only if cited elsewhere",
            ],
            "disallowed": [
                "Track A promotion from triangle or nf5 replication alone",
                "gate 0.55 lowering as success",
                "merge flow sublane pass into lens 0.52 claims",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build()
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"mechanics_ok={doc['mechanics_bundle_ok']} closure_allowed={doc['closure_allowed']}")
    return 0 if doc["mechanics_bundle_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
