from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUB_SCRIPT = ROOT / "scripts" / "premium_multilens_job_queue_stub_v1.py"


def _load_stub_mod():
    spec = importlib.util.spec_from_file_location("premium_multilens_job_queue_stub_v1", STUB_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_queue_entry_v0_relative_path(tmp_path: Path) -> None:
    mod = _load_stub_mod()
    root = tmp_path / "ws"
    root.mkdir()
    rj = root / "reports" / "out.json"
    rj.parent.mkdir(parents=True)
    rj.write_text("{}", encoding="utf-8")
    ent = mod.build_queue_entry_v0(
        job_id="job_test_1",
        queued_at_utc="2026-01-01T00:00:00Z",
        status="queued",
        report_json_path=rj,
        mode="stub",
        root=root,
    )
    assert ent["schema"] == mod.QUEUE_ENTRY_SCHEMA
    assert ent["job_id"] == "job_test_1"
    assert ent["report_json_path"] == "reports/out.json"
    assert ent["report_kind"] == "premium_btrack_multilens_report_v1"
    assert ent["package_mode"] == "stub"


def test_append_queue_line_roundtrip(tmp_path: Path) -> None:
    mod = _load_stub_mod()
    q = tmp_path / "queue.jsonl"
    ent = {
        "schema": mod.QUEUE_ENTRY_SCHEMA,
        "schema_version": mod.QUEUE_ENTRY_SCHEMA_VERSION,
        "job_id": "x",
        "status": "queued",
        "queued_at_utc": "2026-01-02T00:00:00Z",
        "report_json_path": "reports/a.json",
        "report_kind": "premium_btrack_multilens_report_v1",
        "package_mode": "stub",
    }
    mod.append_queue_line_v0(q, ent)
    mod.append_queue_line_v0(q, {**ent, "job_id": "y"})
    lines = q.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["job_id"] == "x"
    assert json.loads(lines[1])["job_id"] == "y"


def test_drain_dry_run_validates_report(tmp_path: Path) -> None:
    mod = _load_stub_mod()
    root = tmp_path / "ws"
    root.mkdir()
    rj = root / "reports" / "prem.json"
    rj.parent.mkdir(parents=True)
    rj.write_text(
        json.dumps({"schema": mod.PREMIUM_REPORT_SCHEMA, "version": "1.0"}, ensure_ascii=False),
        encoding="utf-8",
    )
    q = tmp_path / "q.jsonl"
    mod.append_queue_line_v0(
        q,
        mod.build_queue_entry_v0(
            job_id="j1",
            queued_at_utc="2026-01-01T00:00:00Z",
            status="queued",
            report_json_path=rj,
            mode="stub",
            root=root,
        ),
    )
    cmd = [
        sys.executable,
        str(STUB_SCRIPT),
        "drain",
        "--root",
        str(root),
        "--queue-path",
        str(q),
        "--max-jobs",
        "3",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "job_id=j1" in r.stdout
    assert "ok=True" in r.stdout


def test_drain_dry_run_bad_schema_exits_1(tmp_path: Path) -> None:
    mod = _load_stub_mod()
    root = tmp_path / "ws"
    root.mkdir()
    rj = root / "bad.json"
    rj.write_text("{}", encoding="utf-8")
    q = tmp_path / "q.jsonl"
    mod.append_queue_line_v0(
        q,
        mod.build_queue_entry_v0(
            job_id="j_bad",
            queued_at_utc="2026-01-01T00:00:00Z",
            status="queued",
            report_json_path=rj,
            mode="stub",
            root=root,
        ),
    )
    cmd = [
        sys.executable,
        str(STUB_SCRIPT),
        "drain",
        "--root",
        str(root),
        "--queue-path",
        str(q),
        "--max-jobs",
        "1",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ok=False" in r.stdout


def test_drain_write_ack_skips_repeated(tmp_path: Path) -> None:
    mod = _load_stub_mod()
    root = tmp_path / "ws"
    root.mkdir()
    rj = root / "reports" / "prem.json"
    rj.parent.mkdir(parents=True)
    rj.write_text(
        json.dumps({"schema": mod.PREMIUM_REPORT_SCHEMA, "version": "1.0"}, ensure_ascii=False),
        encoding="utf-8",
    )
    q = tmp_path / "q.jsonl"
    ack = tmp_path / "ack.jsonl"
    ent = mod.build_queue_entry_v0(
        job_id="j_ack",
        queued_at_utc="2026-01-01T00:00:00Z",
        status="queued",
        report_json_path=rj,
        mode="stub",
        root=root,
    )
    mod.append_queue_line_v0(q, ent)
    cmd1 = [
        sys.executable,
        str(STUB_SCRIPT),
        "drain",
        "--root",
        str(root),
        "--queue-path",
        str(q),
        "--ack-path",
        str(ack),
        "--max-jobs",
        "1",
        "--write-ack",
    ]
    r1 = subprocess.run(cmd1, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert ack.is_file()
    lines = ack.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row.get("schema") == mod.ACK_EVENT_SCHEMA
    assert row.get("job_id") == "j_ack"
    assert row.get("ok") is True

    r2 = subprocess.run(cmd1, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "no pending" in r2.stdout.lower()


def test_drain_allow_missing_queue_exits_0(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    missing_q = tmp_path / "nope.jsonl"
    cmd = [
        sys.executable,
        str(STUB_SCRIPT),
        "drain",
        "--root",
        str(root),
        "--queue-path",
        str(missing_q),
        "--allow-missing-queue",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SKIP" in r.stdout


def test_export_pending_writes_json(tmp_path: Path) -> None:
    mod = _load_stub_mod()
    root = tmp_path / "ws"
    root.mkdir()
    rj = root / "reports" / "prem.json"
    rj.parent.mkdir(parents=True)
    rj.write_text(
        json.dumps({"schema": mod.PREMIUM_REPORT_SCHEMA, "version": "1.0"}, ensure_ascii=False),
        encoding="utf-8",
    )
    q = tmp_path / "q.jsonl"
    mod.append_queue_line_v0(
        q,
        mod.build_queue_entry_v0(
            job_id="export_job_1",
            queued_at_utc="2026-02-01T00:00:00Z",
            status="queued",
            report_json_path=rj,
            mode="stub",
            root=root,
        ),
    )
    outj = tmp_path / "pending.json"
    cmd = [
        sys.executable,
        str(STUB_SCRIPT),
        "export-pending",
        "--root",
        str(root),
        "--queue-path",
        str(q),
        "--out-json",
        str(outj),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(outj.read_text(encoding="utf-8"))
    assert data.get("schema") == mod.EXPORT_PENDING_SCHEMA
    assert len(data.get("pending_items", [])) == 1
    assert data["pending_items"][0]["job_id"] == "export_job_1"
    assert data["pending_items"][0]["validation_ok"] is True
    ptrs = data.get("recommended_lens_orchestration_pointers", [])
    assert len(ptrs) >= 4
    assert any("run_myeongni_lens_chain_from_bot_v1.py" in str(p.get("script_workspace_posix", "")) for p in ptrs)


def test_export_pending_allow_missing_queue(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    missing = tmp_path / "no_queue.jsonl"
    outj = tmp_path / "out.json"
    cmd = [
        sys.executable,
        str(STUB_SCRIPT),
        "export-pending",
        "--root",
        str(root),
        "--queue-path",
        str(missing),
        "--out-json",
        str(outj),
        "--allow-missing-queue",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(outj.read_text(encoding="utf-8"))
    assert data.get("pending_items") == []


def test_cli_enqueue_subprocess(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    rj = root / "r.json"
    rj.write_text("{}", encoding="utf-8")
    q = tmp_path / "q.jsonl"
    cmd = [
        sys.executable,
        str(STUB_SCRIPT),
        "enqueue",
        "--root",
        str(root),
        "--queue-path",
        str(q),
        "--job-id",
        "cli_job",
        "--queued-at",
        "2026-03-01T12:00:00Z",
        "--report-json",
        str(rj),
        "--mode",
        "best-effort",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    row = json.loads(q.read_text(encoding="utf-8").strip().splitlines()[0])
    assert row["job_id"] == "cli_job"
    assert row["package_mode"] == "best-effort"
