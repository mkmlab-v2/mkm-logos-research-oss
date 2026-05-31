#!/usr/bin/env python3
"""Harness v2 smoke: deterministic manseryeok engine + optional LLM interpretation only.

B-track only. The engine computes four pillars; the LLM must NOT recompute saju.
Default: verify engine pillars match golden on locked_eval rows, then optional
base-model interpretation envelope generation (no Pack0B saju LoRA — wrong task).

Example::

  py scripts/run_myeongri_harness_v2_engine_interpret_smoke_v1.py --limit 5
  py scripts/run_myeongri_harness_v2_engine_interpret_smoke_v1.py --limit 5 --run-llm --max-new-tokens 320
"""

from __future__ import annotations

import argparse
import hashlib
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
from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict  # noqa: E402
from scripts.myeongri_interpret_envelope_views_v1 import build_harness_v2_interpret_instruction  # noqa: E402

DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_OUT = ROOT / "reports/myeongri_harness_v2_engine_interpret_smoke_v1_latest.json"
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"

PROHIBITION = (
    "B-track hypothesis only; not live trading, medical diagnosis, or doctrinal finality."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


from scripts.myeongri_interpret_envelope_views_v1 import build_harness_v2_interpret_instruction  # noqa: E402


def _build_interpret_instruction(*, deterministic_payload: dict, lang: str, sha256_hex: str) -> str:
    return build_harness_v2_interpret_instruction(
        deterministic_payload=deterministic_payload,
        lang=lang,
        sha256_hex=sha256_hex,
    )


def _load_profile_model_id(profile_json: Path, profile_key: str) -> str:
    data = json.loads(profile_json.read_text(encoding="utf-8"))
    prof = data.get(profile_key) or data.get("profiles", {}).get(profile_key)
    if not isinstance(prof, dict) or not prof.get("model_id"):
        raise SystemExit(f"missing model_id for profile {profile_key!r} in {profile_json}")
    return str(prof["model_id"])


def _try_parse_envelope(
    raw: str,
    *,
    gold_out: dict | None = None,
    postprocess_v1: bool = True,
    compact: dict | None = None,
    lang: str = "ko",
    deterministic_input_sha256: str = "",
    coerce_missing_governance: bool = True,
) -> tuple[dict | None, str, bool]:
    from scripts.myeongri_interpret_envelope_views_v1 import (
        augment_parsed_with_recovered_insight,
        coerce_llm_envelope_to_contract_v1,
        sanitize_interpret_raw_for_parse,
    )
    from scripts.run_myeongri_deterministic_lora_inference_eval_v1 import _extract_json_object

    parsed = augment_parsed_with_recovered_insight(
        _extract_json_object(sanitize_interpret_raw_for_parse(raw)),
        raw,
    )
    if not coerce_missing_governance:
        from scripts.myeongri_interpret_envelope_views_v1 import (
            repair_envelope_fields_v1,
            validate_envelope_required_fields,
        )

        if parsed is None:
            return None, "json_parse_failed", False
        if parsed.get("schema") != "myeongri_ai_interpretation_envelope_v1":
            alt = str(parsed.get("$schema", ""))
            if "myeongri_ai_interpretation_envelope_v1" in alt:
                parsed = {**parsed, "schema": "myeongri_ai_interpretation_envelope_v1"}
        note = validate_envelope_required_fields(parsed)
        if note == "":
            if postprocess_v1:
                parsed = repair_envelope_fields_v1(parsed, gold_out)
            return parsed, "", False
        return parsed, note, False

    return coerce_llm_envelope_to_contract_v1(
        parsed,
        compact=compact,
        lang=lang,
        deterministic_input_sha256=deterministic_input_sha256,
        gold_out=gold_out,
        postprocess_v1=postprocess_v1,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument("--run-llm", action="store_true", help="Run base-model interpretation generation")
    ap.add_argument(
        "--adapter-path",
        type=Path,
        default=None,
        help="Optional PEFT path (default: none — Pack0B saju LoRA is wrong task for interpret)",
    )
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--profile-key", default="train_default")
    ap.add_argument("--model-name", default="", help="Override HF model id")
    ap.add_argument("--max-new-tokens", type=int, default=448)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.9)
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        print(f"missing golden: {args.golden_jsonl}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for line in args.golden_jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    rows = rows[: max(1, int(args.limit))]

    per_row: list[dict] = []
    engine_pass = 0
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
        payload_sha = _sha256_text(_canonical_json(compact))
        rec: dict[str, Any] = {
            "sample_id": sid,
            "engine_path": "prep_myeongri_deterministic_lora_golden_v1.build_golden_row_dict",
            "engine_pillars_match_golden": eng_match,
            "expected_saju": (pillars_view(exp).get("full_saju") or {}).get("saju"),
            "engine_saju": (pillars_view(recomputed).get("full_saju") or {}).get("saju"),
            "deterministic_input_sha256": payload_sha,
        }
        per_row.append(rec)

    llm_ran = False
    llm_parse_ok = 0
    llm_coerced = 0
    if args.run_llm:
        from scripts.run_myeongri_deterministic_lora_inference_eval_v1 import (
            _generate_one,
            _load_model_and_tokenizer,
        )

        model_name = args.model_name.strip() or _load_profile_model_id(args.profile_json, args.profile_key)
        adapter = str(args.adapter_path) if args.adapter_path else ""
        model, tokenizer = _load_model_and_tokenizer(
            model_name,
            adapter,
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
        )
        llm_ran = True
        for i, row in enumerate(rows):
            compact = compact_expected_result(
                build_golden_row_dict(
                    str(row["birth_instant_utc"]),
                    str(row["iana_tz"]),
                    bool(row.get("is_male", False)),
                    str(row["sample_id"]),
                    str(row.get("split", "locked_eval")),
                )["expected_result"]
            )
            sha = per_row[i]["deterministic_input_sha256"]
            instruction = _build_interpret_instruction(
                deterministic_payload=compact, lang=args.lang, sha256_hex=sha
            )
            raw = _generate_one(
                model=model,
                tokenizer=tokenizer,
                instruction=instruction,
                max_new_tokens=int(args.max_new_tokens),
                temperature=float(args.temperature),
                top_p=float(args.top_p),
                repetition_penalty=1.15,
                chat_leak_stop=True,
            )
            parsed, note, coerced = _try_parse_envelope(
                raw,
                compact=compact,
                lang=args.lang,
                deterministic_input_sha256=sha,
            )
            ok = parsed is not None and note == ""
            if ok:
                llm_parse_ok += 1
            if coerced:
                llm_coerced += 1
            per_row[i]["interpretation"] = {
                "parse_ok": ok,
                "mismatch_note": note or None,
                "envelope_coerced_from_template": coerced,
                "raw_head": raw[:400],
                "envelope_schema": (parsed or {}).get("schema"),
            }

    n = len(rows)
    report = {
        "schema": "myeongri_harness_v2_engine_interpret_smoke_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "architecture": "engine_deterministic_then_llm_interpret_only",
        "golden_jsonl": str(args.golden_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "rows": n,
        "engine_pillars_pass_rate": round(engine_pass / n, 6) if n else 0.0,
        "engine_pillars_passed": engine_pass,
        "llm_ran": llm_ran,
        "interpret_envelope_parse_ok_rate": round(llm_parse_ok / n, 6) if llm_ran and n else None,
        "interpret_envelope_parse_ok": llm_parse_ok if llm_ran else None,
        "interpret_envelope_coerced_from_template": llm_coerced if llm_ran else None,
        "interpret_envelope_coerced_rate": round(llm_coerced / n, 6) if llm_ran and n else None,
        "adapter_path": str(args.adapter_path) if args.adapter_path else None,
        "per_row": per_row,
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "engine_pillars_pass_rate": report["engine_pillars_pass_rate"]}))
    if llm_ran:
        print(
            json.dumps(
                {
                    "interpret_envelope_parse_ok_rate": report["interpret_envelope_parse_ok_rate"],
                }
            )
        )
    return 0 if engine_pass == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
