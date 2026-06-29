#!/usr/bin/env python3
"""Grid sweep for Track A shadow optimization parameters (NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
WEIGHTS = ROOT / "reports/tracka_logic_weights_shadow_v1_latest.json"
INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT_DEFAULT = ROOT / "reports/tracka_shadow_sweep_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_perf(weights_path: Path) -> dict[str, Any]:
    cp = subprocess.run(
        [PY, "scripts/run_compression_perf_test_v1.py", "--logic-aware-shadow", "--weights", str(weights_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    doc = _load(ROOT / "reports/compression_perf_test_v1_latest.json") if cp.returncode == 0 else {}
    return {"ok": cp.returncode == 0, "perf": doc, "stdout": (cp.stdout or "")[-200:]}


def build(*, thresholds: list[float], term_caps: list[int]) -> dict[str, Any]:
    base = _load(WEIGHTS)
    weighted = base.get("weighted_terms") or []
    corpus: set[str] = set()
    if INPUT.is_file():
        try:
            eval_doc = json.loads(INPUT.read_text(encoding="utf-8-sig"))
            for row in eval_doc.get("compression_cases") or []:
                raw = str(row.get("raw_text") or "")
                for w in re.findall(r"[A-Za-z0-9_]+|[가-힣]{2,}", raw.lower()):
                    if len(w) >= 2:
                        corpus.add(w)
        except (json.JSONDecodeError, OSError):
            pass
    rows = []
    for thr in thresholds:
        for cap in term_caps:
            filt = [w for w in weighted if float(w.get("normalized_weight") or 0) >= thr][:cap]
            if corpus:
                corpus_hits = [w for w in filt if str(w.get("term") or "").lower() in corpus]
                if corpus_hits:
                    filt = corpus_hits
            temp = ROOT / "reports/_tmp_tracka_logic_weights_shadow_sweep.json"
            tdoc = dict(base)
            tdoc["weighted_terms"] = filt
            tdoc["must_keep_terms_shadow"] = [f.get("term") for f in filt]
            temp.write_text(json.dumps(tdoc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            run = _run_perf(temp)
            perf = run.get("perf") or {}
            delta = perf.get("delta_shadow_minus_raw") or {}
            rows.append(
                {
                    "threshold": thr,
                    "term_cap": cap,
                    "terms_selected": len(filt),
                    "ok": run.get("ok"),
                    "delta_token_saving": delta.get("global_token_saving_rate"),
                    "delta_jaccard": delta.get("avg_reconstruction_fidelity_jaccard"),
                    "delta_sensitive_integrity": delta.get("avg_sensitive_integrity"),
                }
            )
    valid = [r for r in rows if r.get("ok")]
    pareto = sorted(valid, key=lambda r: (-(r.get("delta_jaccard") or -9), (r.get("delta_token_saving") or 9)))[:5]
    return {
        "schema": "tracka_shadow_sweep_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "non_gating": True,
        "research_only": True,
        "track_wall": {"track_a_bridge": False, "live_trading_bridge": False, "policy_mutation_forbidden": True},
        "inputs": {"thresholds": thresholds, "term_caps": term_caps},
        "rows": rows,
        "pareto_top5": pareto,
        "reproduce": "py scripts/run_tracka_shadow_sweep_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--thresholds", default="0.15,0.2,0.25,0.3")
    ap.add_argument("--term-caps", default="8,12,16,24")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]
    caps = [int(x) for x in args.term_caps.split(",") if x.strip()]
    doc = build(thresholds=thresholds, term_caps=caps)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = len(doc.get("pareto_top5") or []) > 0
    print(json.dumps({"ok": ok, "pareto": doc.get("pareto_top5"), "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
