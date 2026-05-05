# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from scripts.build_logos_track_c_freshness_sidecar_v1 import main as freshness_main


def test_sidecar_missing_bundle(tmp_path, monkeypatch):
    out = tmp_path / "fresh.json"
    argv = ["prog", "--bundle", str(tmp_path / "none.json"), "--output", str(out)]
    monkeypatch.setattr("sys.argv", argv)
    assert freshness_main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_track_c_freshness_sidecar_v1"
    assert doc["inputs"]["graph_bundle_present"] is False
    assert doc["freshness"]["staleness_seconds"] is None


def test_sidecar_with_bundle_staleness(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle.json"
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle.write_text(
        json.dumps(
            {
                "schema": "logos_corpus_graph_bundle_v1",
                "ts_utc": past,
                "dedupe_bundle_key_sha256": "a" * 64,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "fresh.json"
    argv = ["prog", "--bundle", str(bundle), "--output", str(out)]
    monkeypatch.setattr("sys.argv", argv)
    assert freshness_main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["inputs"]["graph_bundle_present"] is True
    ss = doc["freshness"]["staleness_seconds"]
    assert isinstance(ss, int)
    assert ss >= 7000
    assert doc["freshness"]["dedupe_bundle_key_sha256_prefix"] == "aaaaaaaaaaaaaaaa…"
