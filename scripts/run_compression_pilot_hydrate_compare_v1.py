#!/usr/bin/env python3
"""Compare baseline PoC vs tenant must_keep overlay (Day 15~30 hydrate proxy)."""

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
TOKEN_RE = re.compile(r"\S+")
DEFAULT_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongni", "bible"}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _token_proxy(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in ("text", "raw_text", "content", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _load_overlay(path: Path) -> set[str]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: set[str] = set()
    for key in ("must_keep_hard_terms", "must_keep_soft_terms"):
        for t in doc.get(key) or []:
            if isinstance(t, str) and t.strip():
                terms.add(t.strip())
    return terms


def _run_baseline_poc(corpus: Path, out: Path, max_cases: int) -> dict[str, Any]:
    proc = subprocess.run(
        [
            PY,
            "scripts/run_customer_compression_stateless_poc_v1.py",
            "--input-jsonl",
            corpus.relative_to(ROOT).as_posix(),
            "--max-cases",
            str(max_cases),
            "--out-json",
            out.relative_to(ROOT).as_posix(),
            "--relax-pass-gate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(f"baseline poc failed: {proc.stderr or proc.stdout}")
    return json.loads(out.read_text(encoding="utf-8-sig"))


def _overlay_metrics(corpus: Path, overlay_terms: set[str], *, max_cases: int) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.compression_profile_v1 import profile_evaluate_report_kwargs_v2
    from scripts.report_multilens_performance_eval import _jaccard, evaluate_report

    prof_kw = profile_evaluate_report_kwargs_v2("economy")
    must_keep = DEFAULT_MUST_KEEP | overlay_terms
    savings: list[float] = []
    jaccards: list[float] = []
    n = 0
    for line in corpus.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or n >= max_cases:
            break
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        text = _row_text(obj)
        if not text:
            continue
        row_id = str(obj.get("id") or f"row_{n}")
        doc = {
            "compression_cases": [
                {
                    "id": row_id,
                    "raw_text": text,
                    "compressed_text": "",
                    "reconstructed_text": "",
                }
            ],
            "fusion_answer_cases": [],
        }
        report = evaluate_report(
            doc,
            source_input="calibration:hydrate_overlay",
            mode="experimental",
            strategy=str(prof_kw["strategy"]),
            intensity=str(prof_kw["intensity"]),
            must_keep=must_keep,
            use_domain_router=bool(prof_kw.get("use_domain_router", True)),
            use_master_codebook_lexicon_v1=bool(prof_kw.get("use_master_codebook_lexicon_v1", True)),
            general_max_saving_rate=prof_kw.get("general_max_saving_rate"),
            sensitive_max_saving_rate=prof_kw.get("sensitive_max_saving_rate"),
            hangul_max_saving_rate=prof_kw.get("hangul_max_saving_rate"),
        )
        comp = report.get("compression_metrics", {})
        cases = comp.get("cases") or []
        if not cases:
            continue
        first = cases[0] if isinstance(cases[0], dict) else {}
        comp_text = str(first.get("compressed_text_effective") or "")
        rec_text = str(first.get("reconstructed_text_effective") or "")
        tin = _token_proxy(text)
        tout = _token_proxy(comp_text)
        saving = max(0.0, 1.0 - (tout / tin)) if tin > 0 else 0.0
        jac = float(_jaccard(text, rec_text))
        savings.append(saving)
        jaccards.append(jac)
        n += 1

    if not savings:
        return {"mean_token_saving_rate_proxy": 0.0, "mean_jaccard_proxy": 0.0, "case_count": 0}
    return {
        "mean_token_saving_rate_proxy": round(sum(savings) / len(savings), 6),
        "mean_jaccard_proxy": round(sum(jaccards) / len(jaccards), 6),
        "case_count": len(savings),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--overlay-json", type=Path, required=True)
    ap.add_argument("--max-cases", type=int, default=25)
    ap.add_argument(
        "--out-json",
        type=Path,
        help="default: reports/compression_pilot_hydrate_compare_<tenant>_v1_latest.json",
    )
    args = ap.parse_args()

    corpus = args.input_jsonl.resolve()
    overlay_path = args.overlay_json.resolve()
    if not corpus.is_file():
        print(f"error: missing corpus: {corpus}", file=sys.stderr)
        return 2
    if not overlay_path.is_file():
        print(f"error: missing overlay: {overlay_path}", file=sys.stderr)
        return 2

    baseline_out = ROOT / f"reports/tmp_hydrate_baseline_{args.tenant_id}_v1.json"
    baseline_doc = _run_baseline_poc(corpus, baseline_out, args.max_cases)
    baseline_agg = baseline_doc.get("aggregate") or {}
    overlay_terms = _load_overlay(overlay_path)
    overlay_agg = _overlay_metrics(corpus, overlay_terms, max_cases=args.max_cases)

    b_save = float(baseline_agg.get("mean_token_saving_rate_proxy") or 0.0)
    o_save = float(overlay_agg.get("mean_token_saving_rate_proxy") or 0.0)
    b_jac = float(baseline_agg.get("mean_jaccard_proxy") or 0.0)
    o_jac = float(overlay_agg.get("mean_jaccard_proxy") or 0.0)

    out = args.out_json or (
        ROOT / f"reports/compression_pilot_hydrate_compare_{args.tenant_id}_v1_latest.json"
    )
    doc = {
        "schema": "compression_pilot_hydrate_compare_v1",
        "generated_at_utc": _utc(),
        "tenant_id": args.tenant_id,
        "labels": ["research_only", "hydrate_window_proxy"],
        "corpus_path": corpus.relative_to(ROOT).as_posix() if corpus.is_relative_to(ROOT) else str(corpus),
        "overlay_path": overlay_path.relative_to(ROOT).as_posix()
        if overlay_path.is_relative_to(ROOT)
        else str(overlay_path),
        "overlay_terms_added": len(overlay_terms),
        "baseline": {
            "arm": "stateless_api_codebook_only",
            "mean_token_saving_rate_proxy": b_save,
            "mean_jaccard_proxy": b_jac,
            "case_count": baseline_doc.get("case_count"),
            "poc_report": baseline_out.relative_to(ROOT).as_posix(),
        },
        "overlay_on": {
            "arm": "evaluate_report_domain_router_plus_overlay",
            "mean_token_saving_rate_proxy": o_save,
            "mean_jaccard_proxy": o_jac,
            "case_count": overlay_agg.get("case_count"),
        },
        "delta": {
            "token_saving_rate_pp_overlay_minus_baseline": round(100 * (o_save - b_save), 4),
            "jaccard_pp_overlay_minus_baseline": round(100 * (o_jac - b_jac), 4),
        },
        "hydrate_window_required": True,
        "boundary_ack": "Overlay arm uses in-process evaluate_report; commercial SLA still requires hydrate window sign-off.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "delta_saving_pp": doc["delta"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
