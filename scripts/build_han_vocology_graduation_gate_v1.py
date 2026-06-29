#!/usr/bin/env python3
"""Build Han Vocology §57 graduation gate report (B-track · M21)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VOLUME_GAP = ROOT / "docs/final/artifacts/han_vocology_volume_gap_v1_latest.json"
OSCE = ROOT / "docs/final/artifacts/han_vocology_osce_rubric_v1_latest.json"
CLOSURE = ROOT / "reports/han_vocology_pilot_closure_v1_latest.json"
JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
OUT_JSON = ROOT / "reports/han_vocology_graduation_gate_v1_latest.json"
OUT_MD = ROOT / "reports/han_vocology_graduation_gate_v1_latest.md"

CORE_POLICIES = {"B1", "A1", "L1", "C1"}
ALLOWED_POLICIES = CORE_POLICIES | {"MDT"}
PASS_MIN = 70
GAP_THRESHOLD = 350.0

RUBRIC: list[tuple[str, str, int]] = [
    ("volume_gap_350", "gap builder ≥350", 20),
    ("osce_55", "OSCE §55", 30),
    ("cb_coverage", "CB-06~16", 25),
    ("policy_spot", "정책 spot", 15),
    ("ethics_hold", "윤리·HOLD", 10),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _osce_valid() -> bool:
    script = ROOT / "scripts/validate_han_vocology_osce_rubric_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--rubric", str(OSCE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _score_volume_gap(gap: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    combined = float((gap.get("summary") or {}).get("combined_total_est") or 0)
    max_pts = 20
    if combined >= GAP_THRESHOLD:
        earned = max_pts
    else:
        earned = int(round(max_pts * combined / GAP_THRESHOLD))
    return earned, {"combined_total_est": combined, "threshold": GAP_THRESHOLD, "earned": earned, "max": max_pts}


def _score_osce(*, skip_validate: bool = False) -> tuple[int, dict[str, Any]]:
    max_pts = 30
    if not OSCE.is_file():
        return 0, {"ok": False, "reason": "rubric_missing"}
    rubric = _load(OSCE)
    stations = rubric.get("stations") or []
    if skip_validate:
        valid = len(stations) == 8
    else:
        valid = _osce_valid()
    earned = max_pts if valid and len(stations) == 8 else 0
    return earned, {
        "validator_ok": valid,
        "station_count": len(stations),
        "earned": earned,
        "max": max_pts,
    }


def _score_cb(closure: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    max_pts = 25
    cb_ids = closure.get("cb_ids") or []
    full = bool(closure.get("cb_full_bank_complete"))
    earned = max_pts if full and len(cb_ids) >= 14 else 0
    return earned, {"cb_full_bank_complete": full, "cb_count": len(cb_ids), "earned": earned, "max": max_pts}


def _score_policy(jsonl: Path) -> tuple[int, dict[str, Any]]:
    max_pts = 15
    rows: list[dict[str, Any]] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    policies = {str(r.get("clinical_policy")) for r in rows if r.get("clinical_policy")}
    invalid = policies - ALLOWED_POLICIES
    core_ok = CORE_POLICIES.issubset(policies)
    all_valid = not invalid
    earned = max_pts if core_ok and all_valid else (10 if all_valid else 0)
    return earned, {
        "policies_seen": sorted(policies),
        "core_policies_ok": core_ok,
        "all_valid": all_valid,
        "earned": earned,
        "max": max_pts,
    }


def _score_ethics(jsonl: Path, closure: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    max_pts = 10
    rows: list[dict[str, Any]] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    hold_ok = all(r.get("send_gate") == "HOLD" for r in rows)
    track_ok = all(r.get("track") == "B" for r in rows)
    closure_hold = closure.get("send_gate") == "HOLD"
    earned = max_pts if hold_ok and track_ok and closure_hold else 0
    return earned, {
        "jsonl_hold": hold_ok,
        "jsonl_track_b": track_ok,
        "closure_hold": closure_hold,
        "earned": earned,
        "max": max_pts,
    }


def build(*, skip_osce_validate: bool = False) -> dict[str, Any]:
    gap = _load(VOLUME_GAP)
    closure = _load(CLOSURE)

    scores: dict[str, dict[str, Any]] = {}
    earned_map: dict[str, int] = {}

    earned_map["volume_gap_350"], scores["volume_gap_350"] = _score_volume_gap(gap)
    earned_map["osce_55"], scores["osce_55"] = _score_osce(skip_validate=skip_osce_validate)
    earned_map["cb_coverage"], scores["cb_coverage"] = _score_cb(closure)
    earned_map["policy_spot"], scores["policy_spot"] = _score_policy(JSONL)
    earned_map["ethics_hold"], scores["ethics_hold"] = _score_ethics(JSONL, closure)

    dimensions = [
        {"id": dim_id, "label_ko": label, "max_points": max_pts, "earned": earned_map[dim_id]}
        for dim_id, label, max_pts in RUBRIC
    ]
    total = sum(earned_map.values())
    passed = total >= PASS_MIN

    return {
        "schema": "han_vocology_graduation_gate_v1",
        "version": "0.1.0",
        "track": "B",
        "send_gate": "HOLD",
        "patient_facing": "blocked",
        "generated_at_utc": _utc(),
        "source_case_bank": "docs/research/HAN_VOCOLOGY_CASE_BANK_V0_1.md",
        "source_section": "§57",
        "pass_min_points": PASS_MIN,
        "total_earned": total,
        "total_max": 100,
        "passed": passed,
        "dimensions": dimensions,
        "detail": scores,
        "inputs": {
            "volume_gap": str(VOLUME_GAP),
            "osce_rubric": str(OSCE),
            "pilot_closure": str(CLOSURE),
            "pilot_jsonl": str(JSONL),
        },
        "disclaimer_ko": "교육·[HYPO] 수료 게이트 — IRB·send_gate 해제·patient-facing 승격과 무관.",
        "reproduce": [
            "py scripts/build_han_vocology_graduation_gate_v1.py",
            "py scripts/validate_han_vocology_graduation_gate_v1.py",
        ],
    }


def _write_md(doc: dict[str, Any]) -> None:
    lines = [
        "# 한의음성학 수료 게이트 (§57 · M21)",
        "",
        f"**Status:** B-track · send_gate HOLD · patient-facing blocked",
        f"**Generated:** {doc['generated_at_utc']}",
        "",
        f"| 지표 | 값 |",
        f"|------|-----|",
        f"| 총점 | **{doc['total_earned']}/{doc['total_max']}** |",
        f"| 합격선 | {doc['pass_min_points']} |",
        f"| 판정 | **{'PASS' if doc['passed'] else 'FAIL'}** |",
        "",
        "## 차원별",
        "",
        "| ID | 항목 | 획득 | 만점 |",
        "|----|------|------|------|",
    ]
    for d in doc["dimensions"]:
        lines.append(f"| {d['id']} | {d['label_ko']} | {d['earned']} | {d['max_points']} |")
    lines += [
        "",
        "## 정책",
        "",
        "- B1 MTD cam+VT · A1 nodules VT first · L1 LPR PPI+diet+VT · C1 SD BoNT",
        "- send_gate HOLD 유지 · patient-facing 금지",
        "",
        "## 재현",
        "",
        "```bash",
        "py scripts/build_han_vocology_graduation_gate_v1.py",
        "py scripts/validate_han_vocology_graduation_gate_v1.py",
        "```",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-osce-validate", action="store_true")
    args = ap.parse_args()

    for path in (VOLUME_GAP, CLOSURE, JSONL):
        if not path.is_file():
            print(json.dumps({"ok": False, "error": f"missing:{path.name}"}, ensure_ascii=False))
            return 1

    doc = build(skip_osce_validate=args.skip_osce_validate)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_md(doc)
    print(
        json.dumps(
            {"ok": True, "passed": doc["passed"], "total": doc["total_earned"], "out": str(OUT_JSON)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
