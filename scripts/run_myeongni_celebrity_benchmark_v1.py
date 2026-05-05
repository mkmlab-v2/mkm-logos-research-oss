#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B-track: run myeongri_core_v2_upgrade logic over curated benchmark rows (JSONL).

Rows may be (1) inline commander_lens fixtures with optional expectations, or
(2) birth_resolution + scores → `run_saju_global_birth_v1.py` for reproducible pillars.

Output: JSON hit-rate summary (no A-track linkage). Does not claim clinical validity.

Paper ↔ MKM contract (Yang 2015): `data/myeongni/paper_contract_maps/yang_2015_four_pillars_personality_map_v1.json`
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "myeongni" / "celebrity_saju_benchmark_v1.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_celebrity_hit_rate_v1.json"


def _run_birth_cli(birth_instant_utc: str, iana_tz: str, is_male: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_saju_global_birth_v1.py"),
        "--utc-instant",
        birth_instant_utc,
        "--iana-tz",
        iana_tz,
        "--compact",
    ]
    if is_male:
        cmd.append("--is-male")
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout or "run_saju_global_birth_v1 failed")
    line = (p.stdout or "").strip()
    if line.startswith("\ufeff"):
        line = line[1:]
    return json.loads(line)


def _commander_from_birth(
    birth: dict[str, Any], *, direction_score: float, confidence: float
) -> dict[str, Any]:
    saj = birth.get("full_saju", {}).get("saju", {})
    if not isinstance(saj, dict):
        return {}
    pillars = {k: str(saj.get(k, "") or "") for k in ("year", "month", "day", "hour")}
    return {
        "schema": "myeongni_independent_lens_v1",
        "scores": {"direction_score": direction_score, "confidence": confidence},
        "advanced": {
            "input_summary": {"pillars": pillars.copy()},
            "slots": {"pillars": pillars.copy(), "sajeong_interpolation": {}, "dayun": []},
        },
    }


def _yang_style_summary(commander: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "btrack_yang_2015_style_metrics_v1",
        ROOT / "scripts" / "btrack_yang_2015_style_metrics_v1.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pl = mod.extract_pillars_from_commander(commander)
    ym = mod.compute_yang_style_metrics(pl)
    return {
        "element_counts_surface_8": ym.get("element_counts_surface_8"),
        "yinyang_counts_surface_8": ym.get("yinyang_counts_surface_8"),
        "six_god_buckets_yang2015_names": ym.get("six_god_buckets_yang2015_names"),
        "day_stem_yinyang": ym.get("day_stem_yinyang"),
    }


def _load_myeongri_v2():
    import importlib.util

    path = ROOT / "scripts" / "myeongri_core_v2_upgrade.py"
    spec = importlib.util.spec_from_file_location("_myeongri_v2", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check_expectations(v2: dict[str, Any], exp: dict[str, Any]) -> tuple[bool, str]:
    detected = v2.get("shinsal_impact_overlay", {}).get("detected", [])
    ids = [str(x.get("id", "")) for x in detected if isinstance(x, dict)]
    for req in exp.get("shinsal_ids_subset", []) or []:
        if str(req) not in ids:
            return False, f"missing shinsal id {req!r}, got {ids!r}"
    for bad in exp.get("shinsal_ids_excluded", []) or []:
        if str(bad) in ids:
            return False, f"unexpected shinsal {bad!r}, got {ids!r}"
    nsm = v2.get("neutral_structure_metrics_v1", {})
    if not isinstance(nsm, dict):
        return False, "missing neutral_structure_metrics_v1"
    t = float(nsm.get("structural_tension_v1", -1.0))
    if "structural_tension_min" in exp and t < float(exp["structural_tension_min"]):
        return False, f"tension {t} < min {exp['structural_tension_min']}"
    if "structural_tension_max" in exp and t > float(exp["structural_tension_max"]):
        return False, f"tension {t} > max {exp['structural_tension_max']}"
    if "state_id" in exp and exp.get("state_id") is not None:
        pb = v2.get("myeongni_16state_probe_nearest_v1")
        if not isinstance(pb, dict):
            return False, "missing myeongni_16state_probe_nearest_v1"
        got_raw = pb.get("nearest_state_id")
        if got_raw is None:
            return False, "nearest_state_id null (16-state probe unavailable)"
        want = int(exp["state_id"])
        if int(got_raw) != want:
            return False, f"state_id expected {want}, nearest_probe={got_raw}"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    mod = _load_myeongri_v2()
    rows_out: list[dict[str, Any]] = []
    evaluated = 0
    passed = 0

    raw_lines = args.dataset.read_text(encoding="utf-8").splitlines()
    for line_no, line in enumerate(raw_lines, start=1):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if str(row.get("schema") or "") != "celebrity_saju_benchmark_row_v1":
            rows_out.append(
                {
                    "line": line_no,
                    "status": "skipped_bad_schema",
                    "detail": row.get("schema"),
                }
            )
            continue

        person_id = str(row.get("person_id") or "")
        status = "ok"
        detail = ""
        commander: dict[str, Any] | None = None

        if isinstance(row.get("commander_lens"), dict):
            commander = row["commander_lens"]
            scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
            if scores and isinstance(commander.get("scores"), dict):
                commander["scores"].update(
                    {
                        "direction_score": float(
                            scores.get("direction_score", commander["scores"].get("direction_score", 0.0))
                        ),
                        "confidence": float(scores.get("confidence", commander["scores"].get("confidence", 0.5))),
                    }
                )
        elif isinstance(row.get("birth_resolution"), dict):
            brs = row["birth_resolution"]
            try:
                birth = _run_birth_cli(
                    str(brs.get("birth_instant_utc") or ""),
                    str(brs.get("iana_tz") or ""),
                    bool(brs.get("is_male")),
                )
            except Exception as e:
                rows_out.append(
                    {
                        "person_id": person_id,
                        "line": line_no,
                        "status": "error_birth_cli",
                        "detail": str(e),
                    }
                )
                continue
            scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
            commander = _commander_from_birth(
                birth,
                direction_score=float(scores.get("direction_score", 0.0) or 0.0),
                confidence=float(scores.get("confidence", 0.55) or 0.55),
            )
            assert_row = row.get("engine_pillar_assert")
            if isinstance(assert_row, dict):
                saj = birth.get("full_saju", {}).get("saju", {})
                mismatch = []
                for k in ("year", "month", "day", "hour"):
                    exp = str(assert_row.get(k) or "")
                    got = str(saj.get(k) or "")
                    if exp and exp != got:
                        mismatch.append(f"{k}: expected {exp!r} got {got!r}")
                if mismatch:
                    rows_out.append(
                        {
                            "person_id": person_id,
                            "line": line_no,
                            "status": "skipped_engine_pillar_drift",
                            "detail": "; ".join(mismatch),
                            "resolution": birth.get("resolution"),
                        }
                    )
                    continue
        else:
            rows_out.append({"person_id": person_id, "line": line_no, "status": "skipped_no_input"})
            continue

        v2 = mod.build_upgrade_doc(commander, source_path=f"benchmark:{person_id}")
        yang_sm = _yang_style_summary(commander)
        exp = row.get("expectations")
        hit: bool | None = None
        msg = ""
        if isinstance(exp, dict) and exp:
            evaluated += 1
            ok, msg = _check_expectations(v2, exp)
            hit = ok
            if ok:
                passed += 1
            else:
                status = "expectation_fail"

        rows_out.append(
            {
                "person_id": person_id,
                "display_name": row.get("display_name"),
                "benchmark_tier": row.get("benchmark_tier"),
                "line": line_no,
                "status": status,
                "expectation_message": msg if isinstance(exp, dict) and exp else "",
                "hit": hit,
                "structural_tension_v1": v2.get("neutral_structure_metrics_v1", {}).get("structural_tension_v1"),
                "shinsal_ids": [
                    str(x.get("id"))
                    for x in (v2.get("shinsal_impact_overlay", {}).get("detected") or [])
                    if isinstance(x, dict)
                ],
                "size_multiplier_recommended": v2.get("output", {}).get("size_multiplier_recommended"),
                "pillars": v2.get("input", {}).get("pillars"),
                "yang_2015_style_metrics": yang_sm,
            }
        )

    summary = {
        "rows_with_expectations": evaluated,
        "expectations_passed": passed,
        "hit_rate": round(passed / evaluated, 6) if evaluated else None,
        "note": "hit_rate counts only rows carrying non-empty expectations; not clinical accuracy.",
    }

    out_doc = {
        "schema": "myeongni_celebrity_hit_rate_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(args.dataset.resolve()),
        "summary": summary,
        "rows": rows_out,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"WROTE: {args.out.resolve()}")
    failed_rows = sum(1 for r in rows_out if r.get("status") == "expectation_fail")
    return 1 if failed_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
