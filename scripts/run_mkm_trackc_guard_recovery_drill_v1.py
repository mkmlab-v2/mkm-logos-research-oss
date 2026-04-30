from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    cp = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return cp.returncode, (cp.stdout + cp.stderr).strip()


def main() -> int:
    root = Path("C:/workspace")
    artifacts = root / "docs" / "final" / "artifacts"
    handoff = artifacts / "mkm_trackc_client_handoff_package_latest.json"
    backup = artifacts / "mkm_trackc_client_handoff_package_latest.backup_drill.json"
    guard_script = root / "scripts" / "check_mkm_trackc_client_handoff_guard.py"
    rebuild_script = root / "scripts" / "build_mkm_trackc_client_handoff_package_v1.py"

    if not handoff.exists():
        raise SystemExit(f"missing handoff artifact: {handoff}")

    shutil.copy2(handoff, backup)
    phase = "corrupt"
    drill: Dict[str, Any] = {
        "schema": "mkm_trackc_guard_recovery_drill_v1",
        "generated_at_utc": _utc_now(),
        "backup_path": str(backup).replace("\\", "/"),
    }

    try:
        doc = _read_json(handoff)
        doc["packet_status"] = "PARTIAL"
        handoff.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

        fail_code, fail_out = _run(
            ["py", str(guard_script), "--workspace-root", str(root)],
            cwd=root,
        )
        drill["fail_phase"] = {
            "exit_code": fail_code,
            "expected_fail": True,
            "output": fail_out[-1200:],
        }

        phase = "rebuild"
        rebuild_code, rebuild_out = _run(["py", str(rebuild_script)], cwd=root)
        drill["rebuild_phase"] = {
            "exit_code": rebuild_code,
            "output": rebuild_out[-1200:],
        }
        if rebuild_code != 0:
            raise RuntimeError("rebuild failed")

        pass_code, pass_out = _run(
            ["py", str(guard_script), "--workspace-root", str(root)],
            cwd=root,
        )
        drill["pass_phase"] = {
            "exit_code": pass_code,
            "expected_pass": True,
            "output": pass_out[-1200:],
        }

        ok = fail_code != 0 and pass_code == 0
        drill["status"] = "PASS" if ok else "FAIL"
        out = artifacts / "mkm_trackc_guard_recovery_drill_latest.json"
        out.write_text(json.dumps(drill, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"drill report written: {out}")
        print(f"status={drill['status']}")
        return 0 if ok else 1
    finally:
        if backup.exists():
            if phase != "rebuild":
                shutil.copy2(backup, handoff)
            backup.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
