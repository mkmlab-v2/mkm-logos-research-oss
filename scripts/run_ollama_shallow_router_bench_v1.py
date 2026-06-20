#!/usr/bin/env python3
"""Local Ollama shallow router bench v1 — parse_ok_rate(raw) + router_hit_rate.

[HYPO] B-track only. Does not open SEND or Track A gates.
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
ENV_PATH = ROOT / ".env"
DEFAULT_OUT = ROOT / "reports/ollama_shallow_router_bench_v1_latest.json"
DEFAULT_FIXTURES = ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.schema.json"
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "mkm-shallow-router-v1"
DEFAULT_MODELFILE = ROOT / "docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt"
THERMO_ALIASES = ("E_i", "P_f", "D_d", "H_c")
OUTPUT_SCHEMA = "ollama_shallow_router_bench_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _host() -> str:
    return (os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/").replace("/v1", "")


def _model_name(override: str | None) -> str:
    if override:
        return override
    return (
        os.getenv("MKM_OLLAMA_SHALLOW_ROUTER_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or DEFAULT_MODEL
    )


def _load_fixtures(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    fixtures = doc.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError(f"fixtures missing in {path}")
    out: list[dict[str, Any]] = []
    for row in fixtures:
        if not isinstance(row, dict):
            continue
        inp = str(row.get("input") or "").strip()
        tag = str(row.get("expected_domain_tag") or "").strip()
        if inp and tag:
            out.append(
                {
                    "id": str(row.get("id") or f"fixture_{len(out)}"),
                    "input": inp,
                    "expected_domain_tag": tag,
                }
            )
    if not out:
        raise ValueError(f"no valid fixtures in {path}")
    return out


def _ollama_reachable(host: str, timeout: int = 5) -> bool:
    try:
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False


def _generate(
    host: str,
    model: str,
    prompt: str,
    timeout: int,
    *,
    json_format: bool = True,
    num_predict: int = 512,
) -> tuple[str, float]:
    url = f"{host}/api/generate"
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.0, "top_p": 0.1},
    }
    if json_format:
        body["format"] = "json"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    latency = time.perf_counter() - start
    return str(doc.get("response") or "").strip(), latency


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    if start < 0:
        return None
    depth = 0
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = cleaned[start : idx + 1]
                try:
                    parsed = json.loads(chunk)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _validate_output_schema(parsed: dict[str, Any], schema_path: Path) -> bool:
    try:
        import jsonschema
    except ImportError:
        return parsed.get("schema") == "ollama_shallow_router_output_v1"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=parsed, schema=schema)
        return True
    except jsonschema.ValidationError:
        return False


def _has_thermo_leak(text: str) -> bool:
    return any(alias in text for alias in THERMO_ALIASES)


def _build_report(
    *,
    mode: str,
    model: str,
    host: str,
    fixtures: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(fixtures)
    parse_ok = sum(1 for r in rows if r.get("parse_ok"))
    router_hit = sum(1 for r in rows if r.get("router_hit"))
    schema_ok = sum(1 for r in rows if r.get("schema_ok"))
    leak_count = sum(1 for r in rows if r.get("leak_violation"))
    raw = {
        "parse_ok_rate": round(parse_ok / total, 4) if total else 0.0,
        "router_hit_rate": round(router_hit / total, 4) if total else 0.0,
        "schema_ok_rate": round(schema_ok / total, 4) if total else 0.0,
        "rows": total,
    }
    return {
        "schema": OUTPUT_SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "mode": mode,
        "model": model,
        "host": host,
        "fixtures_path": str(DEFAULT_FIXTURES.relative_to(ROOT)).replace("\\", "/"),
        "output_schema_path": str(DEFAULT_SCHEMA.relative_to(ROOT)).replace("\\", "/"),
        "modelfile_path": str(DEFAULT_MODELFILE.relative_to(ROOT)).replace("\\", "/"),
        "raw": raw,
        "repair_v2": {
            "note": "No repair layer for shallow router; operational metrics equal raw.",
            "parse_ok_rate": raw["parse_ok_rate"],
            "router_hit_rate": raw["router_hit_rate"],
            "schema_ok_rate": raw["schema_ok_rate"],
            "rows": raw["rows"],
        },
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": 0.0,
        },
        "metrics": {
            **raw,
            "leak_violation_count": leak_count,
        },
        "rows": rows,
    }


def _warmup(host: str, model: str, timeout: int) -> dict[str, Any]:
    try:
        text, latency = _generate(
            host,
            model,
            "Route to infra. Output JSON only.",
            timeout,
            json_format=True,
        )
        return {"ok": bool(text), "latency_sec": round(latency, 4), "preview": text[:200]}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)[:300]}


def run_bench(args: argparse.Namespace) -> int:
    _load_dotenv()
    host = _host()
    model = _model_name(args.model)
    fixtures = _load_fixtures(args.fixtures)

    if args.skip_ollama:
        report = _build_report(
            mode="skipped",
            model=model,
            host=host,
            fixtures=fixtures,
            rows=[
                {
                    "fixture_id": f["id"],
                    "skipped": True,
                    "reason": "skip_ollama",
                }
                for f in fixtures
            ],
        )
        report["skip_reason"] = "skip_ollama"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "skipped": True, "out": str(args.out_json)}, ensure_ascii=False))
        return 0

    if not _ollama_reachable(host, timeout=args.connect_timeout_sec):
        report = _build_report(
            mode="unreachable",
            model=model,
            host=host,
            fixtures=fixtures,
            rows=[
                {
                    "fixture_id": f["id"],
                    "skipped": True,
                    "reason": "ollama_unreachable",
                }
                for f in fixtures
            ],
        )
        report["error"] = "ollama_unreachable"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(args.out_json)}, ensure_ascii=False), file=sys.stderr)
        return 2

    warmup: dict[str, Any] | None = None
    if not args.no_warmup:
        warmup = _warmup(host, model, args.timeout_sec)

    rows: list[dict[str, Any]] = []
    for fix in fixtures:
        row: dict[str, Any] = {
            "fixture_id": fix["id"],
            "expected_domain_tag": fix["expected_domain_tag"],
        }
        try:
            output_text, latency = _generate(
                host,
                model,
                fix["input"],
                args.timeout_sec,
                json_format=not args.no_json_format,
                num_predict=args.num_predict,
            )
            row["latency_sec"] = round(latency, 4)
            row["output_preview"] = output_text[:500]
            parsed = _extract_json_object(output_text)
            row["parse_ok"] = parsed is not None
            row["schema_ok"] = (
                _validate_output_schema(parsed, args.schema) if parsed is not None else False
            )
            row["router_hit"] = (
                isinstance(parsed, dict)
                and parsed.get("domain_tag") == fix["expected_domain_tag"]
            )
            row["leak_violation"] = _has_thermo_leak(output_text)
            if parsed is not None:
                row["parsed_domain_tag"] = parsed.get("domain_tag")
                row["parsed_output"] = parsed
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            row["parse_ok"] = False
            row["schema_ok"] = False
            row["router_hit"] = False
            row["leak_violation"] = False
            row["error"] = str(exc)[:300]
        rows.append(row)

    report = _build_report(mode="live", model=model, host=host, fixtures=fixtures, rows=rows)
    if warmup is not None:
        report["warmup"] = warmup
    report["generate_options"] = {
        "format_json": not args.no_json_format,
        "num_predict": args.num_predict,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    leak_count = int(report["metrics"]["leak_violation_count"])
    print(json.dumps({"ok": leak_count == 0, "out": str(args.out_json), "metrics": report["metrics"]}, ensure_ascii=False))
    if leak_count > 0:
        return 1
    if args.require_parse_ok and report["raw"]["parse_ok_rate"] < args.min_parse_ok_rate:
        return 3
    if args.fail_below_router_hit and report["raw"]["router_hit_rate"] < args.min_router_hit_rate:
        return 4
    if report.get("mode") == "live" and not args.skip_oracle_gap:
        gap_rc = _run_oracle_gap_shadow(args.out_json, args.fixtures)
        report["oracle_gap_shadow"] = {"exit_code": gap_rc, "ok": gap_rc == 0}
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if gap_rc != 0:
            return gap_rc
    return 0


def _run_oracle_gap_shadow(bench_json: Path, fixtures: Path) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_ollama_shallow_routing_oracle_gap_v1.py"),
        "--bench-json",
        str(bench_json),
        "--fixtures",
        str(fixtures),
        "--max-oracle-gap",
        "0.25",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Ollama shallow router bench v1 [HYPO]")
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout-sec", type=int, default=120)
    ap.add_argument("--connect-timeout-sec", type=int, default=5)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--no-warmup", action="store_true")
    ap.add_argument("--no-json-format", action="store_true")
    ap.add_argument("--num-predict", type=int, default=512)
    ap.add_argument("--require-parse-ok", action="store_true")
    ap.add_argument("--min-router-hit-rate", type=float, default=0.0)
    ap.add_argument("--fail-below-router-hit", action="store_true")
    ap.add_argument("--min-parse-ok-rate", type=float, default=0.5)
    ap.add_argument("--skip-oracle-gap", action="store_true")
    args = ap.parse_args()
    return run_bench(args)


if __name__ == "__main__":
    raise SystemExit(main())
