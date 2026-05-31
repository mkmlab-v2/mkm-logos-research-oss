#!/usr/bin/env python3
"""One-shot auto-verify: interpret v4 guard locked100 + leak-truncated recovery (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVAL = ROOT / "reports/myeongri_interpret_lora_v4_eval_locked100_guard448_latest.json"
PREDS = ROOT / "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"
DIV = ROOT / "reports/myeongri_interpret_v4_diversity_audit_locked100_guard448_latest.json"
EVAL_LEGACY = ROOT / "reports/myeongri_interpret_lora_v4_eval_locked100_guard_latest.json"
STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
SAMPLE = ROOT / "reports/myeongri_interpret_v4_human_review_sample_latest.json"
ROW13 = ROOT / "reports/myeongri_interpret_lora_v4_preds_row13_retry_latest.jsonl"


def _fail(msg: str) -> int:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    return 1


def main() -> int:
    global EVAL, PREDS, DIV
    checks: list[dict] = []

    for p in (EVAL, PREDS, DIV, STATUS, SAMPLE):
        if not p.is_file():
            if p in (EVAL, PREDS, DIV) and EVAL_LEGACY.is_file():
                EVAL = EVAL_LEGACY
                PREDS = ROOT / "reports/myeongri_interpret_lora_v4_preds_locked100_guard_latest.jsonl"
                DIV = ROOT / "reports/myeongri_interpret_v4_diversity_audit_locked100_guard_latest.json"
                break
            return _fail(f"missing artifact: {p.relative_to(ROOT)}")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_myeongri_interpret_guard_v1.py",
            "tests/test_myeongri_interpret_postprocess_v1.py",
            "tests/test_audit_myeongri_interpret_narrative_diversity_v1.py",
            "tests/test_build_myeongri_interpret_v4_posteval_bundle_v1.py",
            "-q",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    checks.append(
        {
            "name": "pytest_interpret_bundle",
            "ok": proc.returncode == 0,
            "detail": (proc.stdout or proc.stderr).strip()[-200:],
        }
    )
    if proc.returncode != 0:
        print(json.dumps({"ok": False, "checks": checks}, ensure_ascii=False, indent=2))
        return 1

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audit_myeongri_interpret_narrative_diversity_v1.py"),
            "--eval-json",
            str(EVAL),
            "--predictions-jsonl",
            str(PREDS),
            "--out-json",
            str(DIV),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    checks.append({"name": "diversity_audit_rerun", "ok": proc.returncode == 0, "detail": proc.stdout.strip()})

    div = json.loads(DIV.read_text(encoding="utf-8"))
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))

    gates = {
        "empty_insight_row_count_zero": div.get("empty_insight_row_count") == 0,
        "rows_with_insight_100": div.get("rows_with_insight") == 100,
        "unique_insight_rate_1": div.get("unique_insight_rate") == 1.0,
        "v3_fixed_prefix_rate_0": div.get("v3_fixed_prefix_rate") == 0.0,
        "narrative_diversity_gate_pass": div.get("narrative_diversity_gate_pass") is True,
        "eval_parse_ok_rate_1": eval_doc.get("parse_ok_rate") == 1.0,
        "eval_rows_100": eval_doc.get("rows") == 100,
        "status_empty_insight_0": status.get("v4_variant_sft", {})
        .get("locked100_eval_guard", {})
        .get("empty_insight_row_count")
        == 0,
        "human_review_all_pass": all(
            s.get("reviewer_verdict") == "pass" for s in sample.get("samples") or []
        ),
    }
    if sample.get("human_gate_pass") is not None:
        gates["human_gate_pass"] = sample.get("human_gate_pass") is True
    for k, v in gates.items():
        checks.append({"name": k, "ok": bool(v), "detail": str(v)})

    from scripts.audit_myeongri_interpret_narrative_diversity_v1 import _extract_insight

    if ROW13.is_file():
        raw = json.loads(ROW13.read_text(encoding="utf-8-sig").splitlines()[0])["prediction_raw"]
        ins = _extract_insight(raw)
        checks.append(
            {
                "name": "row13_leak_truncated_recovery",
                "ok": ins is not None and len(ins) >= 8 and ins.startswith("[HYPO]"),
                "detail": (ins or "")[:80],
            }
        )

    preds = [
        json.loads(line)
        for line in PREDS.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    empty_rows = []
    for p in preds:
        ins = _extract_insight(str(p.get("prediction_raw", "")))
        if not ins:
            empty_rows.append(p.get("row_index"))
    checks.append(
        {
            "name": "preds_jsonl_no_empty_insight",
            "ok": len(empty_rows) == 0,
            "detail": empty_rows,
        }
    )

    ok = all(c["ok"] for c in checks)
    print(
        json.dumps(
            {
                "ok": ok,
                "hypothesis_tier": "B",
                "research_only": True,
                "checks": checks,
                "artifacts": {
                    "eval": str(EVAL.relative_to(ROOT)).replace("\\", "/"),
                    "diversity": str(DIV.relative_to(ROOT)).replace("\\", "/"),
                    "status": str(STATUS.relative_to(ROOT)).replace("\\", "/"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
