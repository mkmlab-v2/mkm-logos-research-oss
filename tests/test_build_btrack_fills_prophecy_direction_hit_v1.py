# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_HIT = _ROOT / "scripts" / "build_btrack_fills_prophecy_direction_hit_v1.py"
_OHLCV = _ROOT / "tests" / "fixtures" / "btc_join_hit_ohlcv_smoke_v1.csv"


@pytest.fixture(scope="module")
def overlap_csv(tmp_path_factory: pytest.TempPathFactory) -> Path:
  path = tmp_path_factory.mktemp("overlap") / "overlap.csv"
  src = (
      "utc_date,has_fills,has_prophecy,fill_realized_pnl_sum,prp_predicted_direction\n"
      "2026-01-10,1,1,1.5,bull\n"
      "2026-01-11,1,1,-0.5,bear\n"
      "2026-01-12,1,1,0.0,bull\n"
  )
  path.write_text(src, encoding="utf-8")
  return path


def test_direction_hit_smoke(tmp_path: Path, overlap_csv: Path) -> None:
  out = tmp_path / "hit.json"
  r = subprocess.run(
      [
          sys.executable,
          str(_HIT),
          "--overlap-csv",
          str(overlap_csv),
          "--btc-csv",
          str(_OHLCV),
          "--neutral-bps",
          "2.0",
          "--out-json",
          str(out),
      ],
      cwd=str(_ROOT),
      capture_output=True,
      text=True,
      timeout=60,
  )
  assert r.returncode == 0, r.stderr
  doc = json.loads(out.read_text(encoding="utf-8"))
  assert doc.get("schema") == "btrack_fills_prophecy_direction_hit_v1"
  assert doc.get("research_only") is True
  assert doc.get("ohlcv_leg", {}).get("n_evaluated") == 3
  assert doc.get("pnl_leg", {}).get("n_evaluated") >= 2
  rows = doc.get("rows") or []
  by_date = {row["utc_date"]: row for row in rows}
  assert by_date["2026-01-10"]["ohlcv_actual_direction"] == "bull"
  assert by_date["2026-01-10"]["ohlcv_hit"] is True
