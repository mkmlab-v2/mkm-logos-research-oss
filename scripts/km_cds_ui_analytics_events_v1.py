# -*- coding: utf-8 -*-
"""MKM 한의 CDS UI 모드 전환 분석 이벤트 키 v1 (스크립트·서버 로그용).

프론트 상수와 동일 문자열 유지: projects/no1kmedi/src/lib/km-cds-ui-analytics-events-v1.ts
"""

from __future__ import annotations

from typing import Final

KM_CDS_UI_ANALYTICS_EVENTS_V1: Final[dict[str, str]] = {
    "PUBLIC_MODE_ENTER_ACK": "public_mode_enter_ack_v1",
    "PUBLIC_MODE_EXIT": "public_mode_exit",
    "CDS_MODE_ENTER": "cds_mode_enter",
    "PUBLIC_MODE_ENTER_DECLINED": "public_mode_enter_declined_v1",
    "CDS_MODE_EXIT": "cds_mode_exit",
    # Funnel only — not legal consent (mirrors TS doc).
    "PUBLIC_WORKSPACE_MOUNT_V1": "public_workspace_mount_v1",
    "ADMIN_KPI_ALERT_CLICK_CONSUMER_V1": "admin_kpi_alert_click_consumer_v1",
    "ADMIN_KPI_ALERT_CLICK_SAFETY_V1": "admin_kpi_alert_click_safety_v1",
    "ADMIN_KPI_RECO_CLICK_CONSUMER_V1": "admin_kpi_reco_click_consumer_v1",
    "ADMIN_KPI_RECO_CLICK_SAFETY_V1": "admin_kpi_reco_click_safety_v1",
    "ADMIN_KPI_CHECKLIST_TOGGLE_V1": "admin_kpi_checklist_toggle_v1",
    "ADMIN_KPI_PRIORITY_ACTION_SHOW_V1": "admin_kpi_priority_action_show_v1",
    "ADMIN_KPI_PRIORITY_ACTION_CLICK_V1": "admin_kpi_priority_action_click_v1",
}
