#!/usr/bin/env python3
"""Aggregate TKM encounter_sequence ledger — disagreement + confidence drift [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/encounter_sequence_summary_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_records(paths: list[Path]) -> list[dict[str, Any]]:
    import importlib.util

    ledger_path = ROOT / "scripts" / "encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ledger_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    validate_encounter_sequence_record = mod.validate_encounter_sequence_record

    rows: list[dict[str, Any]] = []
    for path in paths:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            errs = validate_encounter_sequence_record(obj)
            if errs:
                raise ValueError(f"{path} line {i}: {'; '.join(errs)}")
            rows.append(obj)
    return rows


def _discover(paths_arg: list[Path] | None) -> list[Path]:
    if paths_arg:
        return paths_arg
    base = ROOT / "data/clinic"
    found = sorted(base.glob("encounter_sequence_v1*.jsonl"))
    sample = base / "encounter_sequence_v1.sample.jsonl"
    if sample.is_file() and sample not in found:
        found.insert(0, sample)
    return found


def build(*, paths: list[Path] | None = None) -> dict[str, Any]:
    files = _discover(paths)
    records = _load_records(files) if files else []

    closures = [r for r in records if isinstance(r.get("physician_closure"), dict)]
    matches = 0
    disagreement_codes: dict[str, int] = {}
    confidences: list[float] = []
    turn_counts: list[int] = []
    l0_triggers = 0
    label_changes = 0

    for r in records:
        summary = r.get("sequence_summary") if isinstance(r.get("sequence_summary"), dict) else {}
        tc = int(summary.get("turn_count") or 0)
        if tc:
            turn_counts.append(tc)
        fc = summary.get("final_ai_confidence")
        if isinstance(fc, (int, float)):
            confidences.append(float(fc))
        traj = summary.get("constitution_trajectory")
        if isinstance(traj, list) and len(traj) >= 2:
            if len(set(traj)) > 1:
                label_changes += 1
        for ev in r.get("l0_router_events") or []:
            if isinstance(ev, dict) and ev.get("triggered") is True:
                l0_triggers += 1
        for turn in r.get("turns") or []:
            if isinstance(turn, dict):
                l0 = turn.get("l0_red_flag")
                if isinstance(l0, dict) and l0.get("triggered") is True:
                    l0_triggers += 1

    for r in closures:
        agr = r.get("physician_closure", {}).get("agreement") or {}
        if agr.get("ai_physician_match") is True:
            matches += 1
        code = str(agr.get("disagreement_code") or "unknown")
        disagreement_codes[code] = disagreement_codes.get(code, 0) + 1

    closure_n = len(closures)
    physician_agreement_rate = round(matches / closure_n, 4) if closure_n else None
    avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
    avg_turns = round(sum(turn_counts) / len(turn_counts), 2) if turn_counts else None

    summary_ok = len(records) >= 1
    return {
        "schema": "encounter_sequence_summary_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "sasang_primary": True,
        "send_gate": "HOLD",
        "summary_ok": summary_ok,
        "source_files": [str(p).replace("\\", "/") for p in files],
        "sequence_count": len(records),
        "closure_count": closure_n,
        "physician_agreement_rate": physician_agreement_rate,
        "disagreement_code_counts": disagreement_codes,
        "avg_final_ai_confidence": avg_confidence,
        "avg_turn_count": avg_turns,
        "sequences_with_label_change": label_changes,
        "l0_red_flag_trigger_events": l0_triggers,
        "kpi_notes_ko": [
            "physician_agreement_rate = 한의사 골드 vs 최종 AI 가설 일치율 (마케팅용 NLP 승률 아님)",
            "TCM LLM 벤치는 external_reference_only",
        ],
        "reproduce": "py scripts/build_encounter_sequence_summary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, action="append", default=None, help="Ledger JSONL (repeatable)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(paths=args.path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["summary_ok"],
                "sequence_count": doc["sequence_count"],
                "physician_agreement_rate": doc.get("physician_agreement_rate"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["summary_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
