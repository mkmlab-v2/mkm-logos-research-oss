"""Manifest contract for Invoke-MkmCommandPackage_v1.ps1."""



from __future__ import annotations



import json

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

MANIFEST = ROOT / "docs/final/artifacts/mkm_command_package_manifest_v1.json"





def test_manifest_packages_have_steps_and_triggers():

    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))

    assert data["schema"] == "mkm_command_package_manifest_v1"

    assert "excludes_global" in data
    wl = data.get("scheduler_task_whitelist_v1") or {}
    assert wl.get("tasks")
    assert any(t.get("name") == "MKM_WeeklyOpsPatrol" for t in wl["tasks"])

    pkgs = data["packages"]

    assert "OpsSummonLite" in pkgs

    lite = pkgs["OpsSummonLite"]

    assert lite["steps"]

    step_ids = {s["id"] for s in lite["steps"]}

    assert "gem_paste_block" not in step_ids
    assert "constitution_path_sidecar" in step_ids



    summon = pkgs["AthenaSummon"]

    assert summon.get("extends") == "OpsSummonLite"

    assert "아테나 소환" in summon["aliases"]

    athena_ids = {s["id"] for s in summon["steps_after_extend"]}

    assert "evolution_radar_daily" in athena_ids

    assert "athena_automation_registry" in athena_ids



    amsaeng_summon = pkgs["AmsaengSummon"]

    assert amsaeng_summon.get("extends") == "OpsSummonLite"

    assert "암행어사 소환" in amsaeng_summon["chat_triggers"]

    amsaeng_ids = {s["id"] for s in amsaeng_summon["steps_after_extend"]}

    assert "ops_patrol_health" in amsaeng_ids

    assert "cursor_terminal_janitor_daily" in amsaeng_ids



    daily = pkgs["DailyOpsPatrol"]

    assert daily["extends"] == "AthenaSummon"

    assert daily["steps_after_extend"]

    daily_ids = {s["id"] for s in daily["steps_after_extend"]}

    assert "ops_patrol_health" in daily_ids



    weekly = pkgs["WeeklyOpsPatrol"]

    assert weekly["extends"] == "DailyOpsPatrol"

    assert "주간 점검" in weekly["aliases"]

    sched = weekly.get("scheduler_optional") or {}

    assert sched.get("task_name") == "MKM_WeeklyOpsPatrol"

    weekly_ids = {s["id"] for s in weekly["steps_after_extend"]}

    assert "mcp_hygiene_repair_weekly" in weekly_ids

    assert "cursor_terminal_janitor_weekly" in weekly_ids

    assert "inference_batch_dedupe_weekly" in weekly_ids



    full = pkgs["AthenaSummonFull"]

    assert full["extends"] == "OpsSummonLite"

    assert full["steps_after_extend"]



    amsaeng = pkgs["AmsaengPatrol"]

    assert amsaeng.get("extends") == "AmsaengSummon"



    billing = pkgs["BillingPatrol"]

    assert "과금 순찰" in billing["aliases"]

