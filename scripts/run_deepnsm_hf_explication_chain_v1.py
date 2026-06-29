#!/usr/bin/env python3
"""Build HF explication sidecar + paired audit vs gematria [HYPO].

Backends:
  gloss_stub    — offline gloss-overlap (default)
  ollama        — local Ollama weights gloss-assist + gematria index
  hf_checkpoint — upstream baartmar/DeepNSM-1B + gematria index
"""
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.deepnsm_hf_explication_lib_v1 import (  # noqa: E402
    build_hf_stub_explication_record,
    load_gematria_rows,
)
from scripts.deepnsm_shadow_explication_lib_v1 import DEFAULT_GEMATRIA_LEXICON  # noqa: E402

DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/deepnsm_hf_explication_stub_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/deepnsm_hf_explication_chain_v1_latest.json"
DEFAULT_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_hf_stub_v1_latest.json"
GEMATRIA_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _read_audit_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    base = doc.get("baseline") or {}
    return {
        "prime_hit_rate": base.get("prime_hit_rate"),
        "english_only_distortion_rate": base.get("english_only_distortion_rate"),
        "gap_count": base.get("gap_count"),
        "gate_ok": (doc.get("gates") or {}).get("gate_ok"),
    }


def _build_ollama_records(
    samples: list[dict[str, Any]],
    *,
    lexicon: Path,
    model: str | None,
    timeout: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts.deepnsm_hf_ollama_inference_lib_v1 import (  # noqa: E402
        build_hf_ollama_explication_record,
        fetch_ollama_gloss_hints,
        ollama_model,
        ollama_reachable,
        prepare_gematria_index,
    )

    host_model = ollama_model(model)
    if not ollama_reachable():
        raise SystemExit("ollama_unreachable")

    rows, index = prepare_gematria_index(str(lexicon.resolve()))
    records: list[dict[str, Any]] = []
    latencies: list[float] = []
    failures = 0
    for i, sample in enumerate(samples):
        hints = fetch_ollama_gloss_hints(sample, model=host_model, timeout=timeout)
        if not hints.get("ok"):
            failures += 1
        if hints.get("latency_sec") is not None:
            latencies.append(float(hints["latency_sec"]))
        records.append(
            build_hf_ollama_explication_record(
                sample,
                pair_index=i,
                rows=rows,
                index=index,
                ollama_hints=hints,
                model=host_model,
            )
        )
    meta = {
        "ollama_model": host_model,
        "ollama_calls": len(samples),
        "ollama_failures": failures,
        "avg_latency_sec": round(sum(latencies) / len(latencies), 4) if latencies else None,
    }
    return records, meta


def _build_checkpoint_records(
    samples: list[dict[str, Any]],
    *,
    lexicon: Path,
    checkpoint: str | None,
    base_model: str | None,
    max_new_tokens: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts.deepnsm_hf_checkpoint_inference_lib_v1 import (  # noqa: E402
        build_hf_checkpoint_explication_record,
        fetch_checkpoint_gloss_hints,
        load_deepnsm_checkpoint,
        prepare_gematria_index,
    )

    model, tokenizer, ckpt_id, base_id = load_deepnsm_checkpoint(
        checkpoint=checkpoint,
        base_model=base_model,
    )
    rows, index = prepare_gematria_index(str(lexicon.resolve()))
    records: list[dict[str, Any]] = []
    latencies: list[float] = []
    failures = 0
    for i, sample in enumerate(samples):
        hints = fetch_checkpoint_gloss_hints(
            sample,
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=max_new_tokens,
        )
        if not hints.get("ok"):
            failures += 1
        if hints.get("latency_sec") is not None:
            latencies.append(float(hints["latency_sec"]))
        records.append(
            build_hf_checkpoint_explication_record(
                sample,
                pair_index=i,
                rows=rows,
                index=index,
                checkpoint_hints=hints,
                checkpoint_model=ckpt_id,
                base_model=base_id,
            )
        )
    meta = {
        "checkpoint_model": ckpt_id,
        "base_model": base_id,
        "checkpoint_calls": len(samples),
        "checkpoint_failures": failures,
        "avg_latency_sec": round(sum(latencies) / len(latencies), 4) if latencies else None,
    }
    return records, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", choices=("gloss_stub", "ollama", "hf_checkpoint"), default="gloss_stub")
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--gematria-lexicon", type=Path, default=DEFAULT_GEMATRIA_LEXICON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--audit-out", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--max-pairs", type=int, default=0)
    ap.add_argument("--ollama-model", default=None)
    ap.add_argument("--ollama-timeout-sec", type=int, default=120)
    ap.add_argument("--checkpoint-model", default=None)
    ap.add_argument("--checkpoint-base-model", default=None)
    ap.add_argument("--checkpoint-max-new-tokens", type=int, default=128)
    ap.add_argument("--skip-audit", action="store_true")
    ap.add_argument("--skip-ollama-fallback", action="store_true")
    args = ap.parse_args()

    fixture_path = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    if not fixture_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_fixture"}))
        return 2

    samples = json.loads(fixture_path.read_text(encoding="utf-8-sig")).get("samples") or []
    if args.max_pairs > 0:
        samples = samples[: args.max_pairs]

    backend = args.backend
    ollama_meta: dict[str, Any] = {}
    checkpoint_meta: dict[str, Any] = {}
    if backend == "hf_checkpoint":
        try:
            records, checkpoint_meta = _build_checkpoint_records(
                samples,
                lexicon=args.gematria_lexicon,
                checkpoint=args.checkpoint_model,
                base_model=args.checkpoint_base_model,
                max_new_tokens=args.checkpoint_max_new_tokens,
            )
            impl_status = "deepnsm_hf_checkpoint_v1"
        except SystemExit as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))
            return 2
    elif backend == "ollama":
        try:
            records, ollama_meta = _build_ollama_records(
                samples,
                lexicon=args.gematria_lexicon,
                model=args.ollama_model,
                timeout=args.ollama_timeout_sec,
            )
            impl_status = "ollama_local_weights_v1"
        except SystemExit as exc:
            if args.skip_ollama_fallback:
                print(json.dumps({"ok": False, "error": str(exc)}))
                return 2
            backend = "gloss_stub"
            impl_status = "offline_gloss_stub_v1"
            rows = load_gematria_rows(str(args.gematria_lexicon.resolve()))
            records = [
                build_hf_stub_explication_record(sample, pair_index=i, rows=rows)
                for i, sample in enumerate(samples)
            ]
        else:
            impl_status = "ollama_local_weights_v1"
    else:
        impl_status = "offline_gloss_stub_v1"
        rows = load_gematria_rows(str(args.gematria_lexicon.resolve()))
        records = [
            build_hf_stub_explication_record(sample, pair_index=i, rows=rows)
            for i, sample in enumerate(samples)
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    greek_resolved = sum(
        1
        for r in records
        if str((r.get("resolved_probes") or {}).get("greek", {}).get("resolution") or "").startswith(
            ("hf_gloss", "ollama_assist", "checkpoint_assist")
        )
    )
    hebrew_resolved = sum(
        1
        for r in records
        if str((r.get("resolved_probes") or {}).get("hebrew", {}).get("resolution") or "").startswith(
            ("hf_gloss", "ollama_assist", "checkpoint_assist")
        )
    )

    steps: dict[str, Any] = {}
    hf_summary: dict[str, Any] = {}
    if not args.skip_audit:
        proc = subprocess.run(
            [
                PY,
                "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
                "--fixture",
                str(fixture_path),
                "--expected-pairs",
                str(len(samples)),
                "--explication-sidecar",
                str(args.out),
                "--out",
                str(args.audit_out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        steps["hf_audit"] = {
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0,
            "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:],
        }
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "error": "hf_audit_failed", "steps": steps}))
            return 1
        hf_summary = _read_audit_summary(args.audit_out)

    gematria_summary = _read_audit_summary(GEMATRIA_AUDIT)
    delta: dict[str, Any] = {}
    if hf_summary and gematria_summary:
        for key in ("prime_hit_rate", "english_only_distortion_rate"):
            hv = hf_summary.get(key)
            gv = gematria_summary.get(key)
            if hv is not None and gv is not None:
                delta[f"{key}_hf_minus_gematria"] = round(float(hv) - float(gv), 4)

    delta_key = (
        "delta_hf_checkpoint_minus_gematria"
        if impl_status == "deepnsm_hf_checkpoint_v1"
        else (
            "delta_hf_ollama_minus_gematria"
            if impl_status == "ollama_local_weights_v1"
            else "delta_hf_stub_minus_gematria"
        )
    )
    audit_key = (
        "hf_checkpoint_audit"
        if impl_status == "deepnsm_hf_checkpoint_v1"
        else ("hf_ollama_audit" if impl_status == "ollama_local_weights_v1" else "hf_stub_audit")
    )

    report = {
        "schema": "deepnsm_hf_explication_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "implementation_status": impl_status,
        "backend_requested": args.backend,
        "backend_used": backend,
        "ok": True,
        "fixture": _rel(fixture_path),
        "sidecar_out": _rel(args.out),
        "pair_count": len(records),
        "summary": {
            "greek_resolved_count": greek_resolved,
            "hebrew_resolved_count": hebrew_resolved,
            "greek_resolved_rate": round(greek_resolved / max(len(records), 1), 4),
            "hebrew_resolved_rate": round(hebrew_resolved / max(len(records), 1), 4),
        },
        audit_key: hf_summary,
        "gematria_shadow_audit_reference": gematria_summary,
        delta_key: delta,
        "ollama_meta": ollama_meta or None,
        "checkpoint_meta": checkpoint_meta or None,
        "steps": steps,
        "reproduce": f"py scripts/run_deepnsm_hf_explication_chain_v1.py --backend {args.backend}",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Keep stub chain report in sync when running default gloss path on full 500 fixture
    if backend == "gloss_stub" and len(samples) >= 500 and args.report == DEFAULT_REPORT:
        DEFAULT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(args.out),
                "report": _rel(args.report),
                "implementation_status": impl_status,
                "hf_prime_hit": hf_summary.get("prime_hit_rate"),
                "gematria_prime_hit": gematria_summary.get("prime_hit_rate"),
                "delta": delta,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
