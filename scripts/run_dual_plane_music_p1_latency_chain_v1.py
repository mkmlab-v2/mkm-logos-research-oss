#!/usr/bin/env python3
"""P1 music latency chain — symbolic projection + optional Ollama neural draft probe.

Reports latencies on separate planes (FAIL-COMP-004). Ollama is optional; exit 0 when
symbolic bench passes even if Ollama is down (--optional-ollama default).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_dual_plane_music_p1_micro_bench_v1 import (  # noqa: E402
    DEFAULT_FIXTURE,
    apply_trajectory_buffer,
    hard_project_to_allowed,
    is_illegal_root,
    run_bench,
)

PY = sys.executable
DEFAULT_OUT = ROOT / "reports/dual_plane_music_p1_latency_chain_v1_latest.json"
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"
SCHEMA = "dual_plane_music_p1_latency_chain_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    try:
        from dotenv import load_dotenv

        if env_path.is_file():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


def _ollama_host() -> str:
    return (os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/").replace("/v1", "")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL


def probe_ollama(host: str, timeout: int) -> dict[str, Any]:
    url = f"{host}/api/tags"
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        ms = (time.perf_counter() - t0) * 1000.0
        names = [m.get("name") for m in tags.get("models") or [] if isinstance(m, dict)]
        return {"ok": True, "latency_ms": round(ms, 4), "model_names": names[:10]}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": type(exc).__name__, "latency_ms": None}


def _parse_pc(text: str) -> int | None:
    m = re.search(r"\b(1[01]|[0-9])\b", text or "")
    if not m:
        return None
    return int(m.group(1)) % 12


def ollama_draft_pc(
    host: str,
    model: str,
    last_pc: int,
    *,
    timeout: int,
) -> dict[str, Any]:
    prompt = (
        f"C major key. Previous chord root pitch-class (0=C, 11=B): {last_pc % 12}. "
        "Reply with ONE integer 0-11 only for the next chord root pitch-class."
    )
    body = {"model": model, "prompt": prompt, "stream": False}
    url = f"{host}/api/generate"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        ms = (time.perf_counter() - t0) * 1000.0
        text = str(doc.get("response") or "")
        pc = _parse_pc(text)
        return {
            "ok": pc is not None,
            "latency_ms": round(ms, 4),
            "draft_pc": pc,
            "response_excerpt": text[:120],
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "latency_ms": round((time.perf_counter() - t0) * 1000.0, 4), "error": type(exc).__name__}


def run_chain(
    fixture: dict[str, Any],
    *,
    ollama_samples: int,
    ollama_timeout: int,
    skip_ollama: bool,
) -> dict[str, Any]:
    symbolic_report = run_bench(fixture)
    allowed = {int(x) % 12 for x in fixture.get("allowed_root_pcs") or []}
    max_delta = int((fixture.get("buffer_defaults") or {}).get("max_delta_pc", 2))

    ollama_probe: dict[str, Any] = {"skipped": skip_ollama}
    ollama_rows: list[dict[str, Any]] = []
    ollama_latencies: list[float] = []

    if not skip_ollama:
        host = _ollama_host()
        model = _ollama_model()
        ollama_probe = {"host": host, "model": model, **probe_ollama(host, min(ollama_timeout, 15))}

        if ollama_probe.get("ok") and ollama_samples > 0:
            for s in (fixture.get("samples") or [])[:ollama_samples]:
                if not isinstance(s, dict):
                    continue
                last_pc = int(s["last_root_pc"]) % 12
                draft = ollama_draft_pc(host, model, last_pc, timeout=ollama_timeout)
                neural_pc = draft.get("draft_pc")
                row: dict[str, Any] = {
                    "fixture_id": s.get("id"),
                    "last_root_pc": last_pc,
                    "ollama": draft,
                }
                if neural_pc is not None:
                    buffered_pc, _ = apply_trajectory_buffer(last_pc, int(neural_pc), max_delta_pc=max_delta)
                    projected = hard_project_to_allowed(buffered_pc, allowed)
                    row["projected_root_pc"] = projected
                    row["raw_illegal"] = is_illegal_root(int(neural_pc), allowed)
                    row["post_project_illegal"] = is_illegal_root(projected, allowed)
                ollama_rows.append(row)
                if draft.get("latency_ms") is not None:
                    ollama_latencies.append(float(draft["latency_ms"]))

    ollama_latencies.sort()
    p95_idx = min(len(ollama_latencies) - 1, int(len(ollama_latencies) * 0.95)) if ollama_latencies else 0

    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "symbolic_plane": {
            "source": "run_dual_plane_music_p1_micro_bench_v1.run_bench",
            "metrics": symbolic_report.get("metrics"),
            "row_count": symbolic_report.get("row_count"),
        },
        "neural_plane": {
            "source": "optional_ollama_generate",
            "probe": ollama_probe,
            "sample_count": len(ollama_rows),
            "rows": ollama_rows,
            "latency_ms_p95": round(ollama_latencies[p95_idx], 4) if ollama_latencies else None,
            "note": "Neural latency is Ollama generate only — not full music SLM product path",
        },
        "integrity": {"collapsed_combined_score": None},
        "lane_note": "Separate from Universal Root OSS hero — FAIL-COMP-004",
    }


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--ollama-samples", type=int, default=3, help="Ollama draft probes (first N fixture rows)")
    ap.add_argument("--ollama-timeout-sec", type=int, default=120)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument(
        "--optional-ollama",
        action="store_true",
        default=True,
        help="Exit 0 if symbolic ok even when Ollama down (default true)",
    )
    ap.add_argument("--no-optional-ollama", action="store_false", dest="optional_ollama")
    ap.add_argument("--run-micro-bench-subprocess", action="store_true", help="Also refresh micro-bench artifact")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fixture_path = args.fixture.resolve()
    fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))

    if args.run_micro_bench_subprocess:
        subprocess.run(
            [PY, str(ROOT / "scripts/run_dual_plane_music_p1_micro_bench_v1.py"), "--fixture", str(fixture_path)],
            cwd=str(ROOT),
            check=False,
        )

    report = run_chain(
        fixture,
        ollama_samples=args.ollama_samples,
        ollama_timeout=args.ollama_timeout_sec,
        skip_ollama=args.skip_ollama,
    )
    report["fixture"] = _rel(fixture_path)
    report["reproduce"] = (
        "py scripts/run_dual_plane_music_p1_latency_chain_v1.py --run-micro-bench-subprocess"
    )

    symbolic_ok = (report.get("symbolic_plane") or {}).get("metrics", {}).get("post_project_illegal_rate") == 0.0
    neural_ok = args.skip_ollama or (report.get("neural_plane") or {}).get("probe", {}).get("ok") is True
    if args.optional_ollama:
        report["ok"] = symbolic_ok
    else:
        report["ok"] = symbolic_ok and neural_ok

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "symbolic_post_illegal_rate": report["symbolic_plane"]["metrics"]["post_project_illegal_rate"],
                "ollama_probe_ok": report["neural_plane"]["probe"].get("ok"),
                "ollama_latency_ms_p95": report["neural_plane"].get("latency_ms_p95"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
