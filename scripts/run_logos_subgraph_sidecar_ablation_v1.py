#!/usr/bin/env python3
"""Sidecar ablation: subgraph gold eval with each sidecar disabled [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_subgraph_sidecar_ablation_v1_latest.json"

ABLATION_CONFIGS: list[tuple[str, list[str]]] = [
    ("baseline_all_on", []),
    ("no_lemma", ["--disable-lemma-sidecar"]),
    ("no_sinew", ["--disable-sinew-sidecar"]),
    ("no_osi", ["--disable-osi-sidecar"]),
    ("no_theographic", ["--disable-theographic-sidecar"]),
    ("no_gematria", ["--disable-gematria-sidecar"]),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    ap.add_argument("--scratch-dir", type=Path, default=ROOT / "reports/_scratch_sidecar_ablation")
    ap.add_argument("--limit", type=int, default=0, help="Pass --limit to each gold eval subprocess")
    args = ap.parse_args()

    args.scratch_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for label, extra in ABLATION_CONFIGS:
        scratch = args.scratch_dir / f"gold_eval_{label}.json"
        rows.append(_run_eval(label, extra, scratch, limit=args.limit))

    baseline = next((r for r in rows if r["label"] == "baseline_all_on"), {})
    base_hit1 = (baseline.get("hit_at_k_rates") or {}).get("hit_at_1")
    for row in rows:
        hit1 = (row.get("hit_at_k_rates") or {}).get("hit_at_1")
        if base_hit1 is not None and hit1 is not None:
            row["hit_at_1_delta_vs_baseline"] = round(float(hit1) - float(base_hit1), 4)

    all_ok = all(r.get("ok") for r in rows)
    report = {
        "schema": "logos_subgraph_sidecar_ablation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "baseline_hit_at_k_rates": baseline.get("hit_at_k_rates"),
        "configs": rows,
        "reproduce": "py scripts/run_logos_subgraph_sidecar_ablation_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": all_ok, "out": str(args.out), "configs": len(rows)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
