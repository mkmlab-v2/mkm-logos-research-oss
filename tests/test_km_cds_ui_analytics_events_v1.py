# Purpose: KM CDS UI analytics event keys match TS SSOT string values.
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_event_keys_stable() -> None:
    from scripts import km_cds_ui_analytics_events_v1 as m

    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["PUBLIC_MODE_ENTER_ACK"] == "public_mode_enter_ack_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["CDS_MODE_ENTER"] == "cds_mode_enter"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["PUBLIC_WORKSPACE_MOUNT_V1"] == "public_workspace_mount_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_ALERT_CLICK_CONSUMER_V1"] == "admin_kpi_alert_click_consumer_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_ALERT_CLICK_SAFETY_V1"] == "admin_kpi_alert_click_safety_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_RECO_CLICK_CONSUMER_V1"] == "admin_kpi_reco_click_consumer_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_RECO_CLICK_SAFETY_V1"] == "admin_kpi_reco_click_safety_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_CHECKLIST_TOGGLE_V1"] == "admin_kpi_checklist_toggle_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_PRIORITY_ACTION_SHOW_V1"] == "admin_kpi_priority_action_show_v1"
    assert m.KM_CDS_UI_ANALYTICS_EVENTS_V1["ADMIN_KPI_PRIORITY_ACTION_CLICK_V1"] == "admin_kpi_priority_action_click_v1"
    assert len(m.KM_CDS_UI_ANALYTICS_EVENTS_V1) == 13


def test_ts_file_contains_same_strings() -> None:
    ts = (
        ROOT
        / "projects"
        / "no1kmedi"
        / "src"
        / "lib"
        / "km-cds-ui-analytics-events-v1.ts"
    )
    text = ts.read_text(encoding="utf-8")
    for s in (
        "public_mode_enter_ack_v1",
        "public_mode_exit",
        "cds_mode_enter",
        "public_mode_enter_declined_v1",
        "cds_mode_exit",
        "public_workspace_mount_v1",
        "admin_kpi_alert_click_consumer_v1",
        "admin_kpi_alert_click_safety_v1",
        "admin_kpi_reco_click_consumer_v1",
        "admin_kpi_reco_click_safety_v1",
        "admin_kpi_checklist_toggle_v1",
        "admin_kpi_priority_action_show_v1",
        "admin_kpi_priority_action_click_v1",
    ):
        assert s in text
