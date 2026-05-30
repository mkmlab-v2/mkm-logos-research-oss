#!/usr/bin/env python3
"""Quad-Fusion retrain chain v1 — B-track Field lane [HYPO].

Train -> SSOT copy -> quad year rank -> field observational snapshot.
Does NOT trigger live trading or Track A promotion.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_QUAD_SSOT = ROOT / "data" / "quad_fusion_training" / "quad_fusion_result_20260308_230751.json"
RANK_SCRIPT = ROOT / "scripts" / "rank_quad_timeline_year_vs_regime_fingerprints.py"
FIELD_SCRIPT = ROOT / "scripts" / "build_field_regime_observational_snapshot_v1.py"
CHAIN_OUT = ROOT / "reports" / "quad_fusion_retrain_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def _find_latest_result(base: Path) -> Path | None:
    candidates: list[Path] = []
    for folder in (base, base / "rejected"):
        if not folder.is_dir():
            continue
        candidates.extend(folder.glob("quad_fusion_result_*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _run_py(script: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Quad-Fusion retrain chain v1 [HYPO]")
    ap.add_argument("--start-date", default="2022-01-01")
    ap.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--year", type=int, default=datetime.now().year)
    ap.add_argument("--min-correlation-count", type=int, default=3, help="Lower for B-track smoke (default 3)")
    ap.add_argument("--use-gpu", action="store_true", help="Attempt GPU if available (default CPU)")
    ap.add_argument("--quad-ssot", type=Path, default=DEFAULT_QUAD_SSOT)
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    start = _parse_date(args.start_date)
    end = _parse_date(args.end_date)
    use_gpu = bool(args.use_gpu)

    doc: dict = {
        "schema": "quad_fusion_retrain_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "window": {"start": args.start_date, "end": args.end_date, "rank_year": args.year},
        "steps": {},
    }

    if args.dry_run:
        doc["dry_run"] = True
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0

    train_out: Path | None = None
    if not args.skip_train:
        from tools.prophecy.quad_fusion_trainer import QuadFusionTrainer

        trainer = QuadFusionTrainer(use_gpu=use_gpu)
        result = trainer.train_quad_fusion(
            start,
            end,
            min_correlation_count=args.min_correlation_count,
            use_validation=False,
        )
        train_out = _find_latest_result(ROOT / "data" / "quad_fusion_training")
        doc["steps"]["train"] = {
            "exit_code": 0,
            "output_path": str(train_out.relative_to(ROOT)) if train_out else None,
            "canonical_saved": result.get("canonical_saved"),
            "uft_timeline_years": [row.get("year") for row in result.get("uft_v2_timeline") or []],
            "learning_patterns_count": result.get("learning_patterns_count"),
        }
    else:
        train_out = _find_latest_result(ROOT / "data" / "quad_fusion_training")
        doc["steps"]["train"] = {"skipped": True, "output_path": str(train_out.relative_to(ROOT)) if train_out else None}

    if not train_out or not train_out.is_file():
        doc["ok"] = False
        doc["error"] = "no quad_fusion_result JSON after train"
        CHAIN_OUT.parent.mkdir(parents=True, exist_ok=True)
        CHAIN_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": doc["error"]}, ensure_ascii=False))
        return 1

    ssot = args.quad_ssot if args.quad_ssot.is_absolute() else ROOT / args.quad_ssot
    ssot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(train_out, ssot)
    doc["steps"]["ssot_copy"] = {"from": str(train_out.relative_to(ROOT)), "to": str(ssot.relative_to(ROOT))}

    quad_payload = json.loads(ssot.read_text(encoding="utf-8"))
    years = [int(row.get("year")) for row in quad_payload.get("uft_v2_timeline") or [] if row.get("year") is not None]
    doc["uft_v2_timeline_years"] = years

    rank_out = ROOT / "reports" / "field_regime_quad_rank_v1_latest.json"
    rank_rc, rank_log = _run_py(
        RANK_SCRIPT,
        "--year",
        str(args.year),
        "--quad-json",
        str(ssot),
        "--output",
        str(rank_out),
    )
    doc["steps"]["quad_rank"] = {"exit_code": rank_rc, "path": str(rank_out.relative_to(ROOT)), "log_tail": rank_log[-500:]}
    if rank_rc != 0:
        doc["ok"] = False
        CHAIN_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "rank_exit": rank_rc}, ensure_ascii=False))
        return rank_rc

    field_rc, field_log = _run_py(FIELD_SCRIPT, "--quad-json", str(ssot), "--year", str(args.year))
    doc["steps"]["field_snapshot"] = {
        "exit_code": field_rc,
        "path": "reports/field_regime_observational_snapshot_v1_latest.json",
        "log_tail": field_log[-500:],
    }
    if field_rc != 0:
        doc["ok"] = False
        CHAIN_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "field_exit": field_rc}, ensure_ascii=False))
        return field_rc

    snap = json.loads((ROOT / "reports" / "field_regime_observational_snapshot_v1_latest.json").read_text(encoding="utf-8"))
    doc["ok"] = True
    doc["field_primary"] = snap.get("field_layer", {}).get("primary_regime_id_observational")
    doc["field_primary_source"] = snap.get("field_layer", {}).get("primary_source")
    CHAIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "chain": str(CHAIN_OUT.relative_to(ROOT)), "field_primary": doc["field_primary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
