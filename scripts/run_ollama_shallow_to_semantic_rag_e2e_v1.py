#!/usr/bin/env python3
"""E2E: Ollama shallow router output -> handoff -> semantic_rag_bridge bundle [HYPO].

Optional dry-run or live run_question_semantic_rag_bridge_chain_v1 for logos-shaped queries.
Does not open SEND or Track A gates.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/ollama_shallow_to_semantic_rag_e2e_v1_latest.json"
DEFAULT_SHALLOW = ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json"
DEFAULT_HANDOFF = ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_shallow_e2e_v1_latest.json"
DEFAULT_FIXTURES = ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json"
DEFAULT_DOMAIN_EXAMPLES = ROOT / "tests/fixtures/ollama_shallow_e2e_domain_examples_v1.json"
DEEP_CHAIN_OUT = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"

DOMAIN_CALIBRATION = {
    "logos": "logos_4d_state_v1",
    "oracle": "logos_4d_state_v1",
    "myeongni": "myeongri_vector_4d",
    "sasang": "market_sasang_lens_snapshot",
    "infra": "prism_slkm_pointer",
    "devops": "prism_slkm_pointer",
    "design": "prism_slkm_pointer",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    tail = (proc.stdout or "") + (proc.stderr or "")
    return int(proc.returncode), tail.strip()


def _load_handoff_builder():
    path = ROOT / "scripts/build_ollama_shallow_router_handoff_v1.py"
    spec = importlib.util.spec_from_file_location("build_ollama_shallow_router_handoff_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_shallow_from_ollama(query: str, model: str, timeout: int, expected_domain: str = "logos") -> dict[str, Any]:
    bench_path = ROOT / "scripts/run_ollama_shallow_router_bench_v1.py"
    out = ROOT / "reports/ollama_shallow_router_e2e_single_v1_latest.json"
    tmp_fixture = ROOT / "reports/ollama_shallow_e2e_single_fixture_v1.json"
    tmp_fixture.parent.mkdir(parents=True, exist_ok=True)
    tmp_fixture.write_text(
        json.dumps(
            {
                "schema": "ollama_shallow_router_golden_v1",
                "fixtures": [
                    {"id": "e2e_single", "input": query, "expected_domain_tag": expected_domain}
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cmd = [
        PY,
        str(bench_path),
        "--model",
        model,
        "--timeout-sec",
        str(timeout),
        "--no-warmup",
        "--out-json",
        str(out),
        "--fixtures",
        str(tmp_fixture),
    ]
    rc, tail = _run(cmd, timeout=timeout + 30)
    if rc != 0:
        raise RuntimeError(f"ollama shallow bench failed rc={rc}: {tail[-500:]}")
    bench = _read_json(out)
    rows = bench.get("rows") if isinstance(bench.get("rows"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        parsed = row.get("parsed_output")
        if isinstance(parsed, dict):
            return parsed
        preview = str(row.get("output_preview") or "")
        if preview.startswith("{"):
            return json.loads(preview)
    raise RuntimeError("no parseable shallow output from ollama bench")


def _default_query_for_domain(domain: str, fixtures_path: Path) -> str:
    doc = _read_json(fixtures_path)
    for row in doc.get("fixtures", []):
        if isinstance(row, dict) and row.get("expected_domain_tag") == domain:
            return str(row.get("input") or "")
    return "shallow routing smoke query"


def _artifact_ref(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _run_pipeline(
    shallow: dict[str, Any],
    *,
    handoff_out: Path,
    bundle_out: Path,
    include_deep_chain_dry_run: bool,
    include_deep_chain_live: bool,
    query: str,
    query_id: str,
    deep_chain_timeout: int,
) -> tuple[dict[str, Any], int]:
    steps: dict[str, Any] = {}
    if shallow.get("schema") != "ollama_shallow_router_output_v1":
        raise SystemExit("shallow schema must be ollama_shallow_router_output_v1")

    handoff_mod = _load_handoff_builder()
    handoff = handoff_mod.build_handoff(shallow)
    handoff_out.parent.mkdir(parents=True, exist_ok=True)
    handoff_out.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    steps["handoff"] = {"ok": True, "artifact": _artifact_ref(handoff_out)}

    domain = str(shallow.get("domain_tag") or "infra")
    lens_id = handoff.get("lens_route_hint", {}).get("lens_id", "infra")
    cal_kind = DOMAIN_CALIBRATION.get(domain, "prism_slkm_pointer")
    coords = handoff.get("coordinates_slkm") if isinstance(handoff.get("coordinates_slkm"), dict) else {}
    summary = (
        f"Shallow E2E handoff domain={domain} lens={lens_id} "
        f"S/L/K/M={coords.get('S')}/{coords.get('L')}/{coords.get('K')}/{coords.get('M')} [HYPO]"
    )

    bundle_cmd = [
        PY,
        str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
        "--calibration-kind",
        cal_kind,
        "--lens-id",
        str(lens_id),
        "--route-confidence",
        str(handoff.get("lens_route_hint", {}).get("route_confidence_0_1", 0.5)),
        "--summary-line",
        summary,
        "--out",
        str(bundle_out),
        "--gating",
        "NON_GATING" if domain == "logos" else "advisory",
    ]
    rc, tail = _run(bundle_cmd)
    steps["semantic_rag_bridge_bundle"] = {
        "ok": rc == 0,
        "exit_code": rc,
        "artifact": _artifact_ref(bundle_out),
        "calibration_kind": cal_kind,
        "tail": tail[-300:] if rc != 0 else None,
    }
    if rc != 0:
        return steps, rc

    if include_deep_chain_dry_run and domain in {"logos", "oracle"}:
        deep_query = query.strip() or _default_query_for_domain(domain, DEFAULT_FIXTURES)
        deep_cmd = [
            PY,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            deep_query,
            "--query-id",
            query_id,
            "--dry-run",
            "--skip-panorama",
        ]
        rc, tail = _run(deep_cmd, timeout=deep_chain_timeout)
        steps["deep_chain_dry_run"] = {"ok": rc == 0, "exit_code": rc, "tail": tail[-400:]}
        if rc != 0:
            return steps, rc

    if include_deep_chain_live and domain in {"logos", "oracle"}:
        deep_query = query.strip() or _default_query_for_domain(domain, DEFAULT_FIXTURES)
        deep_cmd = [
            PY,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            deep_query,
            "--query-id",
            query_id,
            "--skip-ann-lite",
        ]
        rc, tail = _run(deep_cmd, timeout=deep_chain_timeout)
        steps["deep_chain_live"] = {
            "ok": rc == 0,
            "exit_code": rc,
            "artifact": _artifact_ref(DEEP_CHAIN_OUT),
            "tail": tail[-500:] if rc != 0 else None,
        }
        if rc != 0:
            return steps, rc
        if DEEP_CHAIN_OUT.is_file():
            chain_doc = _read_json(DEEP_CHAIN_OUT)
            steps["deep_chain_live"]["panorama_preflight_ok"] = (
                chain_doc.get("steps", {}).get("panorama_preflight", {}).get("ok")
            )

    return steps, 0


def _write_report(
    *,
    chain_out: Path,
    steps: dict[str, Any],
    shallow: dict[str, Any],
    bundle_out: Path,
    handoff_out: Path,
    shallow_source: dict[str, Any],
    example_id: str | None = None,
) -> None:
    bundle_doc = _read_json(bundle_out) if bundle_out.is_file() else {}
    report: dict[str, Any] = {
        "schema": "ollama_shallow_to_semantic_rag_e2e_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "steps": steps,
        "shallow_source": shallow_source,
        "shallow_domain_tag": str(shallow.get("domain_tag") or "infra"),
        "bundle_lens_route": bundle_doc.get("lens_route"),
        "bundle_validation_ok": (bundle_doc.get("bridge_meta") or {}).get("validation_ok"),
        "artifacts": {
            "handoff": _artifact_ref(handoff_out),
            "bundle": _artifact_ref(bundle_out),
        },
    }
    if example_id:
        report["example_id"] = example_id
    chain_out.parent.mkdir(parents=True, exist_ok=True)
    chain_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Shallow router -> semantic RAG bridge E2E v1 [HYPO]")
    ap.add_argument("--shallow-json", type=Path, default=DEFAULT_SHALLOW)
    ap.add_argument("--run-ollama", action="store_true")
    ap.add_argument("--query", default="", help="Required with --run-ollama")
    ap.add_argument("--expected-domain", default="logos", help="With --run-ollama for bench router_hit")
    ap.add_argument("--model", default="mkm-shallow-router-v1")
    ap.add_argument("--ollama-timeout-sec", type=int, default=180)
    ap.add_argument("--handoff-out", type=Path, default=DEFAULT_HANDOFF)
    ap.add_argument("--bundle-out", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--include-deep-chain-dry-run",
        action="store_true",
        help="dry-run run_question_semantic_rag_bridge_chain_v1 for logos/oracle domains",
    )
    ap.add_argument(
        "--include-deep-chain-live",
        action="store_true",
        help="live run_question_semantic_rag_bridge_chain_v1 (panorama) for logos/oracle domains",
    )
    ap.add_argument("--deep-chain-timeout-sec", type=int, default=360)
    ap.add_argument(
        "--run-domain-examples",
        type=Path,
        default=None,
        help="Run bundle E2E for each example in ollama_shallow_e2e_domain_examples_v1.json",
    )
    ap.add_argument("--query-id", default="shallow_e2e_smoke")
    args = ap.parse_args()

    if args.run_domain_examples is not None:
        examples_path = (
            args.run_domain_examples
            if args.run_domain_examples.is_absolute()
            else ROOT / args.run_domain_examples
        )
        if examples_path == Path("."):
            examples_path = DEFAULT_DOMAIN_EXAMPLES
        doc = _read_json(examples_path)
        matrix_out = ROOT / "reports/ollama_shallow_e2e_domain_matrix_v1_latest.json"
        results: list[dict[str, Any]] = []
        for ex in doc.get("examples", []):
            if not isinstance(ex, dict):
                continue
            ex_id = str(ex.get("id") or "example")
            shallow = ex.get("shallow") if isinstance(ex.get("shallow"), dict) else {}
            with tempfile.TemporaryDirectory(prefix="shallow_e2e_") as tmp:
                tmp_path = Path(tmp)
                handoff_out = tmp_path / f"{ex_id}_handoff.json"
                bundle_out = tmp_path / f"{ex_id}_bundle.json"
                steps, rc = _run_pipeline(
                    shallow,
                    handoff_out=handoff_out,
                    bundle_out=bundle_out,
                    include_deep_chain_dry_run=False,
                    include_deep_chain_live=False,
                    query="",
                    query_id=args.query_id,
                    deep_chain_timeout=args.deep_chain_timeout_sec,
                )
                bundle_doc = _read_json(bundle_out) if bundle_out.is_file() else {}
                lens_id = (bundle_doc.get("lens_route") or {}).get("lens_id")
                cal_kind = (steps.get("semantic_rag_bridge_bundle") or {}).get("calibration_kind")
                bundle_validation_ok = (bundle_doc.get("bridge_meta") or {}).get("validation_ok")
            results.append(
                {
                    "id": ex_id,
                    "ok": rc == 0,
                    "exit_code": rc,
                    "expected_lens_id": ex.get("expected_lens_id"),
                    "actual_lens_id": lens_id,
                    "expected_calibration_kind": ex.get("expected_calibration_kind"),
                    "actual_calibration_kind": cal_kind,
                    "bundle_validation_ok": bundle_validation_ok,
                }
            )
            if rc != 0:
                matrix = {
                    "schema": "ollama_shallow_e2e_domain_matrix_v1",
                    "generated_at_utc": _utc_now(),
                    "results": results,
                    "all_ok": False,
                }
                matrix_out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps({"ok": False, "failed": ex_id, "out": str(matrix_out)}, ensure_ascii=False))
                return rc
        matrix = {
            "schema": "ollama_shallow_e2e_domain_matrix_v1",
            "generated_at_utc": _utc_now(),
            "results": results,
            "all_ok": all(r.get("ok") for r in results),
        }
        matrix_out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "out": str(matrix_out), "count": len(results)}, ensure_ascii=False))
        return 0

    shallow_source: dict[str, Any]
    if args.run_ollama:
        query = str(args.query or "").strip()
        if not query:
            raise SystemExit("--query required with --run-ollama")
        shallow = _resolve_shallow_from_ollama(
            query, args.model, args.ollama_timeout_sec, args.expected_domain
        )
        shallow_source = {"mode": "ollama_live", "model": args.model}
    else:
        shallow_path = args.shallow_json if args.shallow_json.is_absolute() else ROOT / args.shallow_json
        shallow = _read_json(shallow_path)
        shallow_source = {"mode": "file", "path": str(shallow_path.relative_to(ROOT)).replace("\\", "/")}

    handoff_out = args.handoff_out if args.handoff_out.is_absolute() else ROOT / args.handoff_out
    bundle_out = args.bundle_out if args.bundle_out.is_absolute() else ROOT / args.bundle_out
    steps, rc = _run_pipeline(
        shallow,
        handoff_out=handoff_out,
        bundle_out=bundle_out,
        include_deep_chain_dry_run=args.include_deep_chain_dry_run,
        include_deep_chain_live=args.include_deep_chain_live,
        query=str(args.query or ""),
        query_id=args.query_id,
        deep_chain_timeout=args.deep_chain_timeout_sec,
    )
    chain_out = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    _write_report(
        chain_out=chain_out,
        steps=steps,
        shallow=shallow,
        bundle_out=bundle_out,
        handoff_out=handoff_out,
        shallow_source=shallow_source,
    )
    if rc != 0:
        return rc
    print(
        json.dumps(
            {"ok": True, "out": str(chain_out), "domain": shallow.get("domain_tag")},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
