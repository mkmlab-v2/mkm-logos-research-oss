#!/usr/bin/env python3
"""Local RTX en_tech semantic GPU PoC (B-track, research_only, [HYPO]).

Runs literal-profile compression eval on en_tech_spec_stress_v1 cases (CPU path),
then optional sentence-transformer cosine on GPU vs Jaccard — does NOT write Track A.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import BASE_MUST_KEEP  # noqa: E402
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_universal_compression_bench_matrix_sweep_v1 import (  # noqa: E402
    FORBIDDEN,
    MATRIX_INPUT,
    _base_eval_kwargs,
    _metrics,
)

LANE_ID = "en_tech_spec_stress_v1"
DEFAULT_PROFILE = "literal"
SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v2"
LANE_OVERRIDES = ROOT / "docs" / "final" / "artifacts" / "router_lane_shard_overrides_v1.json"
DOMAIN_FLOORS = {"en_tech_spec_stress": None}
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
FROZEN_CPU = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json"
DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MUST_KEEP_PATCH = ROOT / "docs/final/artifacts/en_tech_oov_must_keep_patch_v1.json"

_POOL_MUST_KEEP: frozenset[str] = frozenset(BASE_MUST_KEEP)


def _resolve_must_keep(patch_json: Path | None) -> set[str]:
    mk = set(BASE_MUST_KEEP)
    if patch_json and patch_json.is_file():
        doc = json.loads(patch_json.read_text(encoding="utf-8-sig"))
        extra = doc.get("must_keep_tokens") or []
        mk |= {str(t).strip().lower() for t in extra if str(t).strip()}
    return mk


def _pool_init(mk_tokens: tuple[str, ...]) -> None:
    global _POOL_MUST_KEEP
    _POOL_MUST_KEEP = frozenset(mk_tokens)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nvidia_smi_line() -> str | None:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def _torch_probe() -> dict[str, Any]:
    out: dict[str, Any] = {"available": False}
    try:
        import torch
    except ImportError as exc:
        out["error"] = f"torch_import:{exc}"
        return out
    out["available"] = True
    out["cuda_available"] = bool(torch.cuda.is_available())
    if out["cuda_available"]:
        out["device_name"] = torch.cuda.get_device_name(0)
        out["device_count"] = torch.cuda.device_count()
        try:
            free_b, total_b = torch.cuda.mem_get_info(0)
            out["vram_free_mb"] = round(free_b / (1024 * 1024), 1)
            out["vram_total_mb"] = round(total_b / (1024 * 1024), 1)
        except Exception as exc:  # noqa: BLE001
            out["vram_query_error"] = str(exc)
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_en_tech_cases(
    *,
    use_full_matrix: bool,
    lane_id: str,
    max_cases: int,
    shard_index: int,
    shard_count: int,
) -> list[dict[str, Any]]:
    if use_full_matrix or not (
        ROOT / "docs/final/artifacts/universal_compression_bench_lane_en_tech_spec_stress_v1.json"
    ).is_file():
        doc = json.loads(MATRIX_INPUT.read_text(encoding="utf-8-sig"))
    else:
        doc = json.loads(
            (ROOT / "docs/final/artifacts/universal_compression_bench_lane_en_tech_spec_stress_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
    cases = [
        c
        for c in (doc.get("compression_cases") or [])
        if str(c.get("lane_id") or "") == lane_id
        or str(c.get("domain") or "") == "en_tech_spec_stress"
    ]
    cases.sort(key=lambda c: str(c.get("id") or ""))
    if shard_count > 1:
        cases = [c for i, c in enumerate(cases) if i % shard_count == shard_index]
    if max_cases > 0:
        cases = cases[:max_cases]
    return cases


def _parallel_eval_worker(case: dict[str, Any]) -> dict[str, Any]:
    """ProcessPool entry — re-imports per child (Windows spawn)."""
    shards_root = SHARDS
    odoc = json.loads(LANE_OVERRIDES.read_text(encoding="utf-8-sig"))
    lane_overrides = {str(k): str(v) for k, v in (odoc.get("overrides_by_lane_id") or {}).items()}
    return _eval_case(
        case,
        shards_root=shards_root,
        lane_overrides=lane_overrides,
        must_keep=set(_POOL_MUST_KEEP),
    )


def _eval_case(
    case: dict[str, Any],
    *,
    shards_root: Path,
    lane_overrides: dict[str, str],
    must_keep: set[str] | None = None,
) -> dict[str, Any]:
    src = {"schema": "multilens_performance_eval_input_v1", "compression_cases": [case]}
    kw = _base_eval_kwargs()
    kw.update(profile_evaluate_report_kwargs(DEFAULT_PROFILE))
    lane_id = str(case.get("lane_id") or LANE_ID)
    force_sid = lane_overrides.get(lane_id)
    report = evaluate_report(
        src,
        must_keep=must_keep if must_keep is not None else set(BASE_MUST_KEEP),
        graph_wire_selective_bridge=False,
        emit_semantic_pointer=True,
        force_shard_id=force_sid,
        domain_min_saving_floor_overrides=DOMAIN_FLOORS,
        **kw,
    )
    m = _metrics(report)
    rows = (report.get("compression_metrics") or {}).get("cases") or []
    row = rows[0] if rows else {}
    raw = str(case.get("raw_text") or "")
    rec = str(row.get("reconstructed_text_effective") or row.get("reconstructed_text") or "")
    return {
        "case_id": case.get("id"),
        "metrics": m,
        "raw_text_chars": len(raw),
        "reconstructed_text_chars": len(rec),
        "raw_text_preview": raw[:120],
        "reconstructed_text_preview": rec[:120],
        "_raw_text": raw,
        "_reconstructed_text": rec,
    }


def _semantic_encode(
    model: Any,
    texts: list[str],
    *,
    device: str,
) -> list[list[float]]:
    import torch

    with torch.inference_mode():
        emb = model.encode(
            texts,
            batch_size=min(32, len(texts)),
            normalize_embeddings=True,
            show_progress_bar=False,
            device=device,
        )
    return [e.tolist() if hasattr(e, "tolist") else list(e) for e in emb]


def _host_ram_gb() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        return None


def _resolve_semantic_device(requested: str, torch_info: dict[str, Any]) -> str | None:
    if requested == "skip":
        return None
    if requested == "cpu":
        return "cpu"
    if requested == "cuda":
        return "cuda" if torch_info.get("cuda_available") else None
    # auto: cuda if free VRAM looks OK else cpu (uses system RAM)
    if torch_info.get("cuda_available"):
        free_mb = torch_info.get("vram_free_mb")
        if free_mb is None or float(free_mb) >= 4096:
            return "cuda"
    return "cpu"


def main() -> int:
    ap = argparse.ArgumentParser(description="en_tech local GPU semantic PoC [HYPO]")
    ap.add_argument("--lane-id", default=LANE_ID)
    ap.add_argument("--max-cases", type=int, default=8)
    ap.add_argument("--use-full-matrix", action="store_true", help="UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json")
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--workers", type=int, default=1, help="ProcessPool for compression eval (uses extra RAM)")
    ap.add_argument("--compression-profile", default=DEFAULT_PROFILE)
    ap.add_argument("--st-model", default=DEFAULT_ST_MODEL)
    ap.add_argument("--semantic-device", choices=("auto", "cuda", "cpu", "skip"), default="auto")
    ap.add_argument("--skip-gpu-semantic", action="store_true")
    ap.add_argument("--host-label", default=os.environ.get("COMPUTERNAME", "local"))
    ap.add_argument(
        "--must-keep-patch-json",
        type=Path,
        default=None,
        help="B-track OOV must_keep patch JSON (merged with BASE_MUST_KEEP at eval time)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.compression_profile != DEFAULT_PROFILE:
        print(f"warn: profile {args.compression_profile!r} — spec default is {DEFAULT_PROFILE!r}", file=sys.stderr)

    if args.shard_count < 1 or args.shard_index < 0 or args.shard_index >= args.shard_count:
        print("error: invalid shard-index/count", file=sys.stderr)
        return 1

    cases = _load_en_tech_cases(
        use_full_matrix=args.use_full_matrix,
        lane_id=args.lane_id,
        max_cases=args.max_cases,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
    )
    if not cases:
        print("error: no en_tech cases", file=sys.stderr)
        return 1

    patch_path: Path | None = None
    if args.must_keep_patch_json is not None:
        patch_path = (
            (ROOT / args.must_keep_patch_json).resolve()
            if not args.must_keep_patch_json.is_absolute()
            else args.must_keep_patch_json
        )
    must_keep_set = _resolve_must_keep(patch_path)

    torch_info = _torch_probe()
    ram_gb = _host_ram_gb()
    semantic_device = None if args.skip_gpu_semantic else _resolve_semantic_device(args.semantic_device, torch_info)

    gpu_semantic: dict[str, Any] = {
        "attempted": False,
        "backend": "sentence_transformers",
        "model_id": args.st_model,
        "device_requested": args.semantic_device,
        "device_resolved": semantic_device,
    }

    per_case: list[dict[str, Any]] = []
    texts_raw: list[str] = []
    texts_rec: list[str] = []

    t0 = time.perf_counter()
    workers = max(1, int(args.workers))
    if workers > 1 and len(cases) > 1:
        results_by_id: dict[str, dict[str, Any]] = {}
        init_mk = tuple(sorted(must_keep_set))
        with ProcessPoolExecutor(
            max_workers=min(workers, len(cases)),
            initializer=_pool_init,
            initargs=(init_mk,),
        ) as pool:
            futures = {pool.submit(_parallel_eval_worker, case): case for case in cases}
            for fut in as_completed(futures):
                row = fut.result()
                results_by_id[str(row.get("case_id") or "")] = row
        for case in cases:
            row = results_by_id[str(case.get("id") or "")]
            texts_raw.append(row.pop("_raw_text"))
            texts_rec.append(row.pop("_reconstructed_text"))
            per_case.append(row)
    else:
        odoc = json.loads(LANE_OVERRIDES.read_text(encoding="utf-8-sig"))
        lane_overrides = {str(k): str(v) for k, v in (odoc.get("overrides_by_lane_id") or {}).items()}
        for case in cases:
            row = _eval_case(
                case,
                shards_root=SHARDS,
                lane_overrides=lane_overrides,
                must_keep=must_keep_set,
            )
            texts_raw.append(row.pop("_raw_text"))
            texts_rec.append(row.pop("_reconstructed_text"))
            per_case.append(row)

    compression_elapsed_s = round(time.perf_counter() - t0, 3)

    if semantic_device:
        gpu_semantic["attempted"] = True
        try:
            from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

            model = load_sentence_transformer(args.st_model)
            device = semantic_device
            t1 = time.perf_counter()
            emb_raw = _semantic_encode(model, texts_raw, device=device)
            emb_rec = _semantic_encode(model, texts_rec, device=device)
            gpu_semantic["encode_elapsed_s"] = round(time.perf_counter() - t1, 3)
            cosines: list[float] = []
            for i, pc in enumerate(per_case):
                c = _cosine(emb_raw[i], emb_rec[i])
                cosines.append(c)
                key = "semantic_cosine_gpu" if device == "cuda" else "semantic_cosine_cpu"
                pc[key] = round(c, 6)
            gpu_semantic["cosine_mean"] = round(sum(cosines) / len(cosines), 6) if cosines else None
            gpu_semantic["cosine_min"] = round(min(cosines), 6) if cosines else None
            gpu_semantic["status"] = "ok"
            if device == "cuda":
                import torch

                if torch.cuda.is_available():
                    free_b, total_b = torch.cuda.mem_get_info(0)
                    gpu_semantic["vram_after_encode_free_mb"] = round(free_b / (1024 * 1024), 1)
                    gpu_semantic["vram_after_encode_total_mb"] = round(total_b / (1024 * 1024), 1)
        except Exception as exc:  # noqa: BLE001
            gpu_semantic["status"] = "fail"
            gpu_semantic["error"] = f"{type(exc).__name__}:{exc}"
    elif args.skip_gpu_semantic:
        gpu_semantic["status"] = "skipped_flag"
    else:
        gpu_semantic["status"] = "skipped_no_device"

    jaccards = [float(r["metrics"]["avg_reconstruction_fidelity_jaccard"]) for r in per_case]
    savings = [float(r["metrics"]["global_token_saving_rate"]) for r in per_case]
    agg = {
        "case_count": len(per_case),
        "jaccard_mean": round(sum(jaccards) / len(jaccards), 6) if jaccards else 0.0,
        "jaccard_min": round(min(jaccards), 6) if jaccards else 0.0,
        "saving_mean": round(sum(savings) / len(savings), 6) if savings else 0.0,
        "below_0_85_count": sum(1 for j in jaccards if j < 0.85),
    }

    frozen_ref: dict[str, Any] = {}
    if FROZEN_CPU.is_file():
        fdoc = json.loads(FROZEN_CPU.read_text(encoding="utf-8-sig"))
        frozen_ref = {
            "jaccard_mean_frozen_literal": fdoc.get("aggregate", {}).get("jaccard_mean_frozen_literal"),
            "jaccard_min_frozen_literal": fdoc.get("aggregate", {}).get("jaccard_min_frozen_literal"),
        }
    beat_frozen = (
        agg["jaccard_min"] > 0.758 and agg["jaccard_mean"] > 0.769
        if frozen_ref
        else None
    )

    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out_doc = {
        "schema": "comp_en_tech_semantic_gpu_poc_local_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lane_id": args.lane_id,
        "compression_profile": args.compression_profile,
        "shards_root": "codebook/shards_btrack_router_sharp_v2",
        "host_label": args.host_label,
        "must_keep_patch_json": (
            str(patch_path.relative_to(ROOT)).replace("\\", "/")
            if patch_path and patch_path.is_file()
            else None
        ),
        "must_keep_token_count": len(must_keep_set),
        "shard": {"index": args.shard_index, "count": args.shard_count},
        "parallel_workers": workers if workers > 1 else 1,
        "host_ram_gb": ram_gb,
        "hardware": {
            "nvidia_smi": _nvidia_smi_line(),
            "torch": torch_info,
        },
        "gpu_semantic": gpu_semantic,
        "compression_eval_elapsed_s": compression_elapsed_s,
        "aggregate": agg,
        "frozen_cpu_cross_check": frozen_ref,
        "beat_frozen_cpu_literal_research_only": beat_frozen,
        "p3_lab_gate_note": "Official P3 scaled bench still awaits Innovation Lab GPU credits; this is local 5060 Ti mini PoC only.",
        "track_a_active_written": False,
        "forbidden_write_path": str(FORBIDDEN.relative_to(ROOT)).replace("\\", "/"),
        "per_case": per_case,
        "reporting": {
            "raw": "jaccard + saving from evaluate_report",
            "gpu_semantic": "cosine MiniLM on cuda when available — not a promotion gate",
            "never_claim": [
                "Track A promotion",
                "NVIDIA validation complete",
                "2x throughput",
            ],
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rel = str(out_path.relative_to(ROOT)).replace("\\", "/")
    print(
        json.dumps(
            {
                "wrote": rel,
                "case_count": len(per_case),
                "jaccard_min": agg["jaccard_min"],
                "gpu_semantic_status": gpu_semantic.get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if gpu_semantic.get("status") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
