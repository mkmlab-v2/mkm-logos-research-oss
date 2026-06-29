#!/usr/bin/env python3
"""P3 Root Generator weekly runner — extension chain + replacement logos seed + shallow slice."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.p3_root_generator_lib_v1 import shallow_router_slice  # noqa: E402

BUILD = ROOT / "scripts/build_p3_root_candidate_lexicon_v1.py"
BENCH = ROOT / "scripts/run_p3_root_generator_bench_v1.py"
GATE = ROOT / "scripts/check_p3_root_generator_bench_gate_v1.py"
NSM_AUDIT = ROOT / "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py"
HANGUL_CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot"
    / "master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json"
)
BUILD_REPORT = ROOT / "reports/p3_root_candidate_lexicon_build_v1_latest.json"
PROBE = ROOT / "tests/fixtures/p3_root_extension_probe_v1.jsonl"
ALIAS = ROOT / "tests/fixtures/herbs_formulas_alias_table_minimal_v1.json"
OUT_WEEKLY = ROOT / "reports/p3_root_generator_weekly_v1_latest.json"
DEFAULT_OUT = OUT_WEEKLY


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def _read_candidate() -> Path | None:
    if not BUILD_REPORT.is_file():
        return None
    rel = json.loads(BUILD_REPORT.read_text(encoding="utf-8")).get("candidate_path")
    if not rel:
        return None
    p = ROOT / str(rel)
    return p if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline-shallow", action="store_true", help="Skip live Ollama shallow slice")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-replacement", action="store_true")
    ap.add_argument("--compression-sample", type=int, default=5)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report: dict[str, Any] = {
        "schema": "p3_root_generator_weekly_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "steps": {},
    }

    if not args.skip_pytest:
        code = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_p3_root_generator_bench_v1.py",
                "tests/test_build_p3_root_candidate_lexicon_v1.py",
                "tests/test_p3_root_generator_lib_v1.py",
                "-q",
            ]
        )
        report["steps"]["pytest"] = {"exit_code": code}
        if code != 0:
            _write_out(args.out, report, ok=False)
            return code

    build_cmd = [
        sys.executable,
        str(BUILD),
        "--slug",
        "weekly_extension",
        "--extension-jsonl",
        str(PROBE),
        "--alias-table",
        str(ALIAS),
    ]
    code = _run(build_cmd)
    report["steps"]["build_extension"] = {"exit_code": code}
    if code != 0:
        _write_out(args.out, report, ok=False)
        return code

    candidate = _read_candidate()
    if candidate is None:
        report["error"] = "candidate_missing_after_build"
        _write_out(args.out, report, ok=False)
        return 1

    bench_cmd = [
        sys.executable,
        str(BENCH),
        "--profile",
        "extension",
        "--candidate-lexicon",
        str(candidate),
        "--compression-sample",
        str(args.compression_sample),
    ]
    code = _run(bench_cmd)
    report["steps"]["bench_extension"] = {"exit_code": code}
    if code != 0:
        _write_out(args.out, report, ok=False)
        return code

    code = _run([sys.executable, str(GATE)])
    report["steps"]["gate_extension"] = {"exit_code": code}
    gate_doc = json.loads((ROOT / "reports/p3_root_generator_bench_gate_v1_latest.json").read_text(encoding="utf-8"))
    report["extension"] = {
        "decision": gate_doc.get("decision"),
        "reasons": gate_doc.get("reasons"),
    }
    if code != 0 or gate_doc.get("decision") not in {"ADVANCE_EXTENSION_CANDIDATE"}:
        _write_out(args.out, report, ok=False)
        return code or 1

    if not args.skip_replacement:
        repl_cmd = [
            sys.executable,
            str(BUILD),
            "--profile",
            "replacement",
            "--seed-logos-atoms-from-baseline",
            "--slug",
            "weekly_replacement_logos_seed",
            "--extension-jsonl",
            str(PROBE),
            "--alias-table",
            str(ALIAS),
        ]
        code = _run(repl_cmd)
        report["steps"]["build_replacement"] = {"exit_code": code}
        if code == 0:
            repl_candidate = _read_candidate()
            if repl_candidate is not None:
                _run(
                    [
                        sys.executable,
                        str(BENCH),
                        "--profile",
                        "replacement",
                        "--candidate-lexicon",
                        str(repl_candidate),
                        "--compression-sample",
                        str(min(3, args.compression_sample)),
                    ]
                )
                _run([sys.executable, str(GATE)])
                build_doc = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
                gate_doc = json.loads(
                    (ROOT / "reports/p3_root_generator_bench_gate_v1_latest.json").read_text(encoding="utf-8")
                )
                report["replacement"] = {
                    "status": "ok",
                    "candidate_row_count": build_doc.get("candidate_row_count"),
                    "decision": gate_doc.get("decision"),
                    "reasons": gate_doc.get("reasons"),
                    "note": "HOLD expected for replacement research lane",
                }

    shallow = shallow_router_slice(skip_ollama=args.offline_shallow)
    report["shallow_router"] = shallow

    nsm_code = _run([sys.executable, str(NSM_AUDIT)])
    report["steps"]["nsm_crosswalk_audit"] = {"exit_code": nsm_code}
    nsm_path = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
    if nsm_path.is_file():
        nsm_doc = json.loads(nsm_path.read_text(encoding="utf-8"))
        report["nsm_crosswalk"] = {
            "prime_hit_rate": (nsm_doc.get("baseline") or {}).get("prime_hit_rate"),
            "distortion_rate": (nsm_doc.get("baseline") or {}).get("english_only_distortion_rate"),
            "research_verdict": "high_distortion_expected_nsm_vs_corpus_lexicon"
            if (nsm_doc.get("baseline") or {}).get("english_only_distortion_rate", 0) > 0.5
            else "moderate_crosswalk",
            "gate_ok": (nsm_doc.get("gates") or {}).get("gate_ok"),
        }

    if HANGUL_CANDIDATE.is_file():
        hangul_bench = [
            sys.executable,
            str(BENCH),
            "--profile",
            "extension",
            "--candidate-lexicon",
            str(HANGUL_CANDIDATE),
            "--out",
            str(ROOT / "reports/p3_root_generator_bench_hangul41676_v1_latest.json"),
            "--compression-sample",
            str(min(3, args.compression_sample)),
        ]
        h_code = _run(hangul_bench)
        h_gate = _run(
            [
                sys.executable,
                str(GATE),
                "--bench",
                str(ROOT / "reports/p3_root_generator_bench_hangul41676_v1_latest.json"),
                "--out",
                str(ROOT / "reports/p3_root_generator_bench_gate_hangul41676_v1_latest.json"),
            ]
        )
        hangul_gate_doc = {}
        hangul_gate_path = ROOT / "reports/p3_root_generator_bench_gate_hangul41676_v1_latest.json"
        if hangul_gate_path.is_file():
            hangul_gate_doc = json.loads(hangul_gate_path.read_text(encoding="utf-8"))
        report["steps"]["hangul41676_bench"] = {"exit_code": h_code}
        report["steps"]["hangul41676_gate"] = {"exit_code": h_gate}
        report["hangul41676"] = {
            "decision": hangul_gate_doc.get("decision"),
            "promotion": "HOLD",
        }

    paste_code = _run([sys.executable, str(ROOT / "scripts/build_p3_root_generator_ops_paste_v1.py")])
    report["steps"]["ops_paste"] = {"exit_code": paste_code}

    _write_out(args.out, report, ok=True)
    print(json.dumps({"ok": True, "weekly": str(args.out), "extension_decision": report["extension"]["decision"]}))
    return 0 if paste_code == 0 else paste_code


def _write_out(path: Path, report: dict[str, Any], *, ok: bool) -> None:
    report["ok"] = ok
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
