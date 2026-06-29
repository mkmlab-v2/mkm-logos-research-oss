#!/usr/bin/env python3
"""Harness v2 dual-pass PoC: insight generation (pass1) + format wrap (pass2).

B-track [HYPO] only. Pass2 default is deterministic template merge (no LLM).
Optional pass2 LLM uses format-wrap instruction with focus0007-style adapter.

Example (CI / no GPU)::

  py scripts/run_myeongri_harness_v2_dual_pass_poc_v1.py --dry-run --limit 10

Example (GPU, small smoke)::

  py scripts/run_myeongri_harness_v2_dual_pass_poc_v1.py --run-llm --limit 5 \\
    --pass1-adapter storage/adapters/myeongri_interpret_lora_v0/run_interpret_harness_train_s32_hn_v1

Compare vs single-pass baseline::

  py scripts/run_myeongri_harness_v2_dual_pass_poc_v1.py --dry-run --limit 100 \\
    --baseline-report reports/myeongri_harness_v2_engine_interpret_smoke_locked100_interpret_s32_hn_v1.json
"""

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

from scripts.myeongri_deterministic_lora_golden_views_v1 import (  # noqa: E402
    compact_expected_result,
    pillars_view,
)
from scripts.myeongri_interpret_envelope_views_v1 import (  # noqa: E402
    build_harness_v2_format_wrap_instruction,
    build_harness_v2_insight_only_instruction,
    dual_pass_deterministic_format_v1,
    extract_mkm_insight_from_llm_parsed,
    insight_from_engine_compact,
    template_envelope_from_compact,
    validate_envelope_required_fields,
)
from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict  # noqa: E402
from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import (  # noqa: E402
    _canonical_json,
    _load_profile_model_id,
    _sha256_text,
    _try_parse_envelope,
)

DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_OUT = ROOT / "reports/myeongri_harness_v2_dual_pass_poc_v1_latest.json"
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
DEFAULT_PASS1_ADAPTER = (
    ROOT / "storage/adapters/myeongri_interpret_lora_v0/run_interpret_harness_train_s32_hn_v1"
)
DEFAULT_PASS2_ADAPTER = (
    ROOT / "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_qwen_compact_focus0007_s8_v1"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_golden_rows(path: Path, limit: int) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows[: max(1, int(limit))]


def _row_compact(row: dict) -> dict:
    recomputed = build_golden_row_dict(
        str(row["birth_instant_utc"]),
        str(row["iana_tz"]),
        bool(row.get("is_male", False)),
        str(row["sample_id"]),
        str(row.get("split", "locked_eval")),
    )["expected_result"]
    return compact_expected_result(recomputed)


def _baseline_coerced_ids(report_path: Path) -> set[str]:
    if not report_path.is_file():
        return set()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for rec in data.get("per_row") or []:
        interp = rec.get("interpretation") or {}
        if interp.get("envelope_coerced_from_template"):
            out.add(str(rec.get("sample_id")))
    return out


def _pass1_insight_dry_run(*, compact: dict, lang: str, sample_id: str) -> str:
    env = template_envelope_from_compact(
        compact,
        lang=lang,
        sample_id=sample_id,
        method_id="dual_pass_poc_pass1_dry_run_v1",
    )
    return str(env.get("mkm_advanced_insight") or insight_from_engine_compact(compact, lang=lang))


def _normalize_pass1_prose(raw: str) -> str:
    from scripts.myeongri_interpret_envelope_views_v1 import normalize_pass1_insight_prose_v1

    text = (raw or "").strip()
    if not text:
        return ""
    if text.startswith("{") and "mkm_advanced_insight" in text:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            got = extract_mkm_insight_from_llm_parsed(obj, raw=text)
            if got:
                return normalize_pass1_insight_prose_v1(got)
    return normalize_pass1_insight_prose_v1(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument("--dry-run", action="store_true", help="Pass1 uses template insight; pass2 deterministic")
    ap.add_argument("--run-llm", action="store_true", help="Run pass1 LLM (requires GPU)")
    ap.add_argument(
        "--pass2-mode",
        default="deterministic",
        choices=("deterministic", "llm"),
        help="Pass2: template merge (default) or format-wrap LLM",
    )
    ap.add_argument("--pass1-adapter", type=Path, default=DEFAULT_PASS1_ADAPTER)
    ap.add_argument("--pass2-adapter", type=Path, default=DEFAULT_PASS2_ADAPTER)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--profile-key", default="train_default")
    ap.add_argument("--model-name", default="")
    ap.add_argument("--pass1-max-new-tokens", type=int, default=320)
    ap.add_argument("--pass2-max-new-tokens", type=int, default=448)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument(
        "--baseline-report",
        type=Path,
        default=None,
        help="Single-pass harness report for whack-a-mole delta (optional)",
    )
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        print(f"missing golden: {args.golden_jsonl}", file=sys.stderr)
        return 2
    if args.run_llm and args.dry_run:
        print("choose one of --dry-run or --run-llm", file=sys.stderr)
        return 2
    if not args.run_llm and not args.dry_run:
        args.dry_run = True

    rows = _load_golden_rows(args.golden_jsonl, args.limit)
    baseline_coerced = _baseline_coerced_ids(args.baseline_report) if args.baseline_report else set()

    per_row: list[dict] = []
    engine_pass = 0
    pass1_ok = 0
    pass2_parse_ok = 0
    pass2_intentional_merge = 0
    pass2_llm_coerced_recovery = 0
    whack_fixed = 0

    pass1_model = pass1_tokenizer = None
    pass2_model = pass2_tokenizer = None
    if args.run_llm:
        from scripts.run_myeongri_deterministic_lora_inference_eval_v1 import (
            _generate_one,
            _load_model_and_tokenizer,
        )

        model_name = args.model_name.strip() or _load_profile_model_id(args.profile_json, args.profile_key)
        pass1_model, pass1_tokenizer = _load_model_and_tokenizer(
            model_name,
            str(args.pass1_adapter),
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
        )
        if args.pass2_mode == "llm":
            pass2_model, pass2_tokenizer = _load_model_and_tokenizer(
                model_name,
                str(args.pass2_adapter),
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
            )

    for row in rows:
        sid = str(row["sample_id"])
        exp = row["expected_result"]
        recomputed = build_golden_row_dict(
            str(row["birth_instant_utc"]),
            str(row["iana_tz"]),
            bool(row.get("is_male", False)),
            sid,
            str(row.get("split", "locked_eval")),
        )["expected_result"]
        eng_match = _canonical_json(pillars_view(recomputed)) == _canonical_json(pillars_view(exp))
        if eng_match:
            engine_pass += 1
        compact = compact_expected_result(recomputed)
        sha = _sha256_text(_canonical_json(compact))

        pass1_raw = ""
        if args.dry_run:
            pass1_insight = _pass1_insight_dry_run(compact=compact, lang=args.lang, sample_id=sid)
        else:
            instruction = build_harness_v2_insight_only_instruction(
                deterministic_payload=compact,
                lang=args.lang,
                sha256_hex=sha,
            )
            pass1_raw = _generate_one(
                model=pass1_model,
                tokenizer=pass1_tokenizer,
                instruction=instruction,
                max_new_tokens=int(args.pass1_max_new_tokens),
                temperature=float(args.temperature),
                top_p=float(args.top_p),
                repetition_penalty=1.15,
                chat_leak_stop=True,
            )
            pass1_insight = _normalize_pass1_prose(pass1_raw)

        pass1_ok_flag = len((pass1_insight or "").strip()) >= 8
        if pass1_ok_flag:
            pass1_ok += 1

        pass2_note = ""
        pass2_coerced_recovery = False
        pass2_intentional = False
        envelope: dict[str, Any] | None = None

        if args.pass2_mode == "deterministic":
            envelope, pass2_note, used_insight = dual_pass_deterministic_format_v1(
                pass1_insight=pass1_insight,
                compact=compact,
                lang=args.lang,
                deterministic_input_sha256=sha,
            )
            pass2_intentional = bool(used_insight)
            pass2_ok = validate_envelope_required_fields(envelope) == ""
        else:
            wrap_instruction = build_harness_v2_format_wrap_instruction(
                deterministic_payload=compact,
                lang=args.lang,
                sha256_hex=sha,
                pass1_insight=pass1_insight,
            )
            pass2_raw = _generate_one(
                model=pass2_model,
                tokenizer=pass2_tokenizer,
                instruction=wrap_instruction,
                max_new_tokens=int(args.pass2_max_new_tokens),
                temperature=0.1,
                top_p=float(args.top_p),
                repetition_penalty=1.1,
                chat_leak_stop=True,
            )
            envelope, pass2_note, pass2_coerced_recovery = _try_parse_envelope(
                pass2_raw,
                compact=compact,
                lang=args.lang,
                deterministic_input_sha256=sha,
                coerce_missing_governance=True,
            )
            pass2_ok = envelope is not None and pass2_note == ""

        if pass2_ok:
            pass2_parse_ok += 1
        if pass2_intentional:
            pass2_intentional_merge += 1
        if pass2_coerced_recovery:
            pass2_llm_coerced_recovery += 1

        fixed_baseline = sid in baseline_coerced and not pass2_coerced_recovery
        if fixed_baseline:
            whack_fixed += 1

        per_row.append(
            {
                "sample_id": sid,
                "engine_pillars_match_golden": eng_match,
                "deterministic_input_sha256": sha,
                "pass1": {
                    "mode": "dry_run_template" if args.dry_run else "llm_insight_only",
                    "insight_ok": pass1_ok_flag,
                    "insight_head": (pass1_insight or "")[:240],
                    "raw_head": (pass1_raw or "")[:240] or None,
                },
                "pass2": {
                    "mode": args.pass2_mode,
                    "parse_ok": pass2_ok,
                    "mismatch_note": pass2_note or None,
                    "intentional_template_merge": pass2_intentional,
                    "coerced_recovery": pass2_coerced_recovery,
                    "envelope_schema": (envelope or {}).get("schema"),
                },
                "baseline_single_pass_coerced": sid in baseline_coerced,
                "whack_a_mole_fixed_vs_baseline": fixed_baseline,
            }
        )

    n = len(rows)
    report = {
        "schema": "myeongri_harness_v2_dual_pass_poc_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "architecture": "engine_deterministic_pass1_insight_pass2_format",
        "golden_jsonl": str(args.golden_jsonl.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "rows": n,
        "pass1_mode": "dry_run_template" if args.dry_run else "llm_insight_only",
        "pass2_mode": args.pass2_mode,
        "pass1_adapter": str(args.pass1_adapter) if args.run_llm else None,
        "pass2_adapter": str(args.pass2_adapter) if args.run_llm and args.pass2_mode == "llm" else None,
        "baseline_report": (
            str(args.baseline_report.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
            if args.baseline_report
            else None
        ),
        "engine_pillars_pass_rate": round(engine_pass / n, 6) if n else 0.0,
        "pass1_insight_ok_rate": round(pass1_ok / n, 6) if n else 0.0,
        "pass2_envelope_parse_ok_rate": round(pass2_parse_ok / n, 6) if n else 0.0,
        "pass2_intentional_template_merge_rate": round(pass2_intentional_merge / n, 6) if n else 0.0,
        "pass2_llm_coerced_recovery_rate": round(pass2_llm_coerced_recovery / n, 6) if n else 0.0,
        "whack_a_mole_fixed_vs_baseline_count": whack_fixed,
        "delta_vs_baseline": {
            "baseline_coerced_count": len(baseline_coerced),
            "dual_pass_coerced_recovery_count": pass2_llm_coerced_recovery,
            "note": (
                "deterministic pass2: coerced_recovery expected 0; intentional_template_merge expected 1.0"
                if args.pass2_mode == "deterministic"
                else "llm pass2: compare coerced_recovery to baseline single-pass"
            ),
        },
        "per_row": per_row,
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "pass2_envelope_parse_ok_rate": report["pass2_envelope_parse_ok_rate"],
                "pass2_llm_coerced_recovery_rate": report["pass2_llm_coerced_recovery_rate"],
            }
        )
    )
    return 0 if engine_pass == n and pass2_parse_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
