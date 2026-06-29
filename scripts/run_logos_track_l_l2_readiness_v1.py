#!/usr/bin/env python3
"""Track L L2 readiness: deterministic verse resolve before ANN (philosophy pilot + pytest)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
L1_SCRIPT = ROOT / "scripts/run_logos_track_l_l1_readiness_v1.py"
PILOT = ROOT / "scripts/philosophy_lane_rag_pilot_v1.py"
RESOLVER_TEST = ROOT / "tests/test_resolve_logos_verse_reference_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l2_readiness_v1_latest.json"
L2_QUERY = "What does John 19:34 say about blood and water?"
EXPECTED_VERSE = "Jhn.19.34"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _run_py(args: list[str], *, timeout: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode, tail[-1200:] if len(tail) > 1200 else tail


def _check_l1() -> dict[str, Any]:
    rc, tail = _run_py([str(L1_SCRIPT)], timeout=180)
    l1_path = ROOT / "docs/final/artifacts/logos_track_l_l1_readiness_v1_latest.json"
    l1_ok = False
    if l1_path.is_file():
        try:
            l1_ok = bool(json.loads(l1_path.read_text(encoding="utf-8")).get("l1_ok"))
        except json.JSONDecodeError:
            l1_ok = False
    return {"exit_code": rc, "l1_ok": l1_ok and rc == 0, "tail": tail}


def _check_philosophy_pilot_verse_resolve() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="track_l_l2_") as tmp:
        out = Path(tmp) / "pilot_l2_smoke.json"
        rc, tail = _run_py(
            [
                str(PILOT),
                "--user-query",
                L2_QUERY,
                "--out",
                str(out),
            ],
            timeout=300,
        )
        check: dict[str, Any] = {
            "exit_code": rc,
            "output_json": str(out),
            "tail": tail,
        }
        if not out.is_file():
            check["ok"] = False
            check["error"] = "pilot_output_missing"
            return check
        doc = json.loads(out.read_text(encoding="utf-8"))
        vrr = doc.get("verse_reference_resolve") if isinstance(doc.get("verse_reference_resolve"), dict) else {}
        primary = vrr.get("primary_verse_id")
        resolved = vrr.get("resolved") or []
        rails = doc.get("rails_used") or []
        check.update(
            {
                "primary_verse_id": primary,
                "resolved_count": len(resolved) if isinstance(resolved, list) else 0,
                "has_deterministic_rail": "logos_verse_reference_resolve_v1" in rails,
                "track_l_rail": vrr.get("track_l_rail"),
                "ok": (
                    rc == 0
                    and primary == EXPECTED_VERSE
                    and isinstance(resolved, list)
                    and len(resolved) >= 1
                    and "logos_verse_reference_resolve_v1" in rails
                ),
            }
        )
        return check


def _check_resolver_pytest() -> dict[str, Any]:
    rc, tail = _run_py(["-m", "pytest", str(RESOLVER_TEST), "-q"], timeout=180)
    return {"exit_code": rc, "ok": rc == 0, "tail": tail}


def build_report(*, skip_l1: bool) -> dict[str, Any]:
    l1 = {"skipped": True, "l1_ok": True} if skip_l1 else _check_l1()
    pilot = _check_philosophy_pilot_verse_resolve()
    pytest_check = _check_resolver_pytest()
    l2_ok = bool(
        (l1.get("skipped") or l1.get("l1_ok"))
        and pilot.get("ok")
        and pytest_check.get("ok")
    )
    return {
        "schema": "logos_track_l_l2_readiness_v1",
        "generated_at_utc": _utc_now(),
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
            "deterministic_before_ann": True,
        },
        "l2_ok": l2_ok,
        "checks": {
            "l1_prerequisite": l1,
            "philosophy_pilot_verse_reference_resolve": pilot,
            "resolver_pytest": pytest_check,
        },
        "pointer": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md §L2",
        "l2_query_smoke": L2_QUERY,
        "expected_primary_verse_id": EXPECTED_VERSE,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Track L L2 readiness bundle")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-l1", action="store_true")
    args = ap.parse_args(argv)

    doc = build_report(skip_l1=args.skip_l1)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["l2_ok"], "wrote": str(out)}, ensure_ascii=False))
    return 0 if doc["l2_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
