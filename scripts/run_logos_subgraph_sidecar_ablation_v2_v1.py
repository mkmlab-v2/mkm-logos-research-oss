#!/usr/bin/env python3
"""Sidecar ablation v2: single-off + all-off + pairwise OFF matrix on gold 48 [HYPO]."""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_subgraph_sidecar_ablation_v2_latest.json"

SIDECAR_FLAGS: list[tuple[str, str]] = [
    ("lemma", "--disable-lemma-sidecar"),
    ("sinew", "--disable-sinew-sidecar"),
    ("osi", "--disable-osi-sidecar"),
    ("theographic", "--disable-theographic-sidecar"),
    ("gematria", "--disable-gematria-sidecar"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hit_at_1(rates: dict[str, Any] | None) -> float | None:
    if not rates:
        return None
    val = rates.get("1", rates.get("hit_at_1"))
    return float(val) if val is not None else None


def _build_configs(*, quick: bool = False) -> list[tuple[str, list[str]]]:
    configs: list[tuple[str, list[str]]] = [("baseline_all_on", [])]
    for name, flag in SIDECAR_FLAGS:
        configs.append((f"no_{name}", [flag]))
    all_off = [flag for _, flag in SIDECAR_FLAGS]
    configs.append(("all_off", all_off))
    pairs = list(itertools.combinations(SIDECAR_FLAGS, 2))
    if quick:
        pairs = [pairs[0]] if pairs else []
    for (n1, f1), (n2, f2) in pairs:
        configs.append((f"off_{n1}_{n2}", [f1, f2]))
    return configs


def _run_eval(label: str, extra_args: list[str], out_json: Path, *, limit: int = 0) -> dict[str, Any]:
    cmd = [PY, "scripts/run_logos_subgraph_gold_eval_v1.py", "--out-json", str(out_json), *extra_args]
    if limit > 0:
        cmd.extend(["--limit", str(limit)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    doc: dict[str, Any] = {}
    if out_json.is_file():
        try:
            doc = json.loads(out_json.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            doc = {}
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    return {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "hit_at_k_rates": summary.get("hit_at_k_rates"),
        "gold_required_all_pass": summary.get("gold_required_all_pass"),
        "items_evaluated": summary.get("items_evaluated"),
        "report_path": (
            str(out_json.relative_to(ROOT)).replace("\\", "/")
            if str(out_json.resolve()).startswith(str(ROOT.resolve()))
            else str(out_json)
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--scratch-dir", type=Path, default=ROOT / "reports/_scratch_sidecar_ablation_v2")
    ap.add_argument("--limit", type=int, default=0, help="Pass --limit to each gold eval subprocess")
    ap.add_argument("--quick", action="store_true", help="baseline + singles + all_off + one pairwise only")
    args = ap.parse_args()

    args.scratch_dir.mkdir(parents=True, exist_ok=True)
    configs = _build_configs(quick=args.quick)
    rows: list[dict[str, Any]] = []
    for label, extra in configs:
        scratch = args.scratch_dir / f"gold_eval_{label}.json"
        rows.append(_run_eval(label, extra, scratch, limit=args.limit))

    baseline = next((r for r in rows if r["label"] == "baseline_all_on"), {})
    base_hit1 = _hit_at_1(baseline.get("hit_at_k_rates"))
    regressions: list[str] = []
    for row in rows:
        hit1 = _hit_at_1(row.get("hit_at_k_rates"))
        if base_hit1 is not None and hit1 is not None:
            row["hit_at_1_delta_vs_baseline"] = round(hit1 - base_hit1, 4)
            if hit1 < base_hit1:
                regressions.append(str(row["label"]))
        row["matches_baseline_hit_at_1"] = hit1 == base_hit1 if hit1 is not None and base_hit1 is not None else None

    all_ok = all(r.get("ok") for r in rows)
    no_regression = not regressions
    report = {
        "schema": "logos_subgraph_sidecar_ablation_v2",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "no_hit_at_1_regression": no_regression,
        "regression_labels": regressions,
        "config_count": len(rows),
        "quick_mode": args.quick,
        "baseline_hit_at_k_rates": baseline.get("hit_at_k_rates"),
        "configs": rows,
        "reproduce": "py scripts/run_logos_subgraph_sidecar_ablation_v2_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": all_ok and no_regression,
                "out": str(args.out),
                "configs": len(rows),
                "regressions": regressions,
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok and no_regression else 1


if __name__ == "__main__":
    raise SystemExit(main())
