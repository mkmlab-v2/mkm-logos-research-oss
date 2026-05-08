#!/usr/bin/env python3
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
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROBE = ROOT / "scripts" / "logos_vector_resonance_probe.py"
DEFAULT_REGIME_MAP = ROOT / "data" / "regimes" / "regime_map.json"
DEFAULT_OUT = ART / "logos_regime_resonance_shadow_signal_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_probe(probe: Path, regime_map: Path, regime: str, top_k: int, out_path: Path) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(probe),
        "--rank-by-regime",
        "--regime",
        regime,
        "--regime-map",
        str(regime_map),
        "--top-k",
        str(int(top_k)),
        "--output",
        str(out_path),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        return cp.returncode, (cp.stderr or cp.stdout).strip()[:400]
    return 0, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build non-gating Logos regime resonance shadow signal.")
    ap.add_argument("--probe-script", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--regime-map-json", type=Path, default=DEFAULT_REGIME_MAP)
    ap.add_argument("--regimes", type=str, default="lehman,covid,imf,it_bubble")
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    probe = args.probe_script if args.probe_script.is_absolute() else ROOT / args.probe_script
    regime_map = args.regime_map_json if args.regime_map_json.is_absolute() else ROOT / args.regime_map_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    regimes = [r.strip() for r in args.regimes.split(",") if r.strip()]

    result: dict[str, Any] = {
        "schema": "logos_regime_resonance_shadow_signal_v1",
        "generated_at_utc": _now(),
        "status": "UNKNOWN",
        "regimes_requested": regimes,
        "rows": [],
        "summary": {},
        "track_wall": {"shadow_only": True, "auto_trade_enable": False, "non_gating_signal_only": True},
        "evidence_paths": {
            "probe_script": str(probe.resolve()),
            "regime_map_json": str(regime_map.resolve()),
        },
    }

    if not probe.is_file():
        result["status"] = "SKIPPED_MISSING_PROBE_SCRIPT"
        result["summary"] = {"scanned_regimes": 0, "errors": 1}
    elif not regime_map.is_file():
        result["status"] = "SKIPPED_MISSING_REGIME_MAP"
        result["summary"] = {"scanned_regimes": 0, "errors": 1}
    elif not regimes:
        result["status"] = "SKIPPED_NO_REGIMES"
        result["summary"] = {"scanned_regimes": 0, "errors": 1}
    else:
        with tempfile.TemporaryDirectory(prefix="logos_regime_resonance_") as td:
            tmp = Path(td)
            rows: list[dict[str, Any]] = []
            for regime in regimes:
                out_probe = tmp / f"{regime}_resonance.json"
                rc, err = _run_probe(probe=probe, regime_map=regime_map, regime=regime, top_k=int(args.top_k), out_path=out_probe)
                if rc != 0 or not out_probe.is_file():
                    rows.append({"regime": regime, "status": "error", "error": err or f"probe_rc_{rc}"})
                    continue
                doc = _read_json(out_probe)
                hits = doc.get("hits") if isinstance(doc.get("hits"), list) else []
                top = hits[0] if hits and isinstance(hits[0], dict) else {}
                rows.append(
                    {
                        "regime": regime,
                        "status": "ok",
                        "verses_scanned": int(doc.get("verses_scanned") or 0),
                        "top_hit_verse_id": top.get("verse_id"),
                        "top_hit_cosine_to_regime": top.get("cosine_to_regime_fingerprint_4d"),
                    }
                )
            ok_rows = [r for r in rows if r.get("status") == "ok"]
            best = None
            if ok_rows:
                best = max(ok_rows, key=lambda r: float(r.get("top_hit_cosine_to_regime") or -1.0))
            result["rows"] = rows
            result["status"] = "OK" if len(ok_rows) == len(regimes) else ("PARTIAL" if ok_rows else "ERROR")
            result["summary"] = {
                "scanned_regimes": len(ok_rows),
                "requested_regimes": len(regimes),
                "errors": len(regimes) - len(ok_rows),
                "best_regime": (best or {}).get("regime"),
                "best_top_hit_cosine": (best or {}).get("top_hit_cosine_to_regime"),
            }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "status": result["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

