# Domain A HOLD — auto demo capture v0

**상태:** `research_only` · `send_gate: HOLD` · **auto capture DONE** · Loom cloud upload **NOT done**  
**생성:** 2026-07-17T12:17:12Z  
**URL (로컬):** `http://127.0.0.1:8765/`

## What this is

자동으로 dogfood UI를 띄우고 샷 리스트를 걸어 **PNG + flipbook(+optional video)** 을 만든 **녹화 대체물**.

## Files

- `reports/domain_a_demo_shots/01_ui_pass.png`
- `reports/domain_a_demo_shots/02_ui_hold.png`
- `reports/domain_a_demo_shots/03_audit_api.png`
- `reports/domain_a_demo_shots/04_cli_synthetic_sop.png`
- flipbook: `reports/domain_a_demo_shots/flipbook.html`
- video: `reports/domain_a_demo_shots/domain_a_hold_auto_demo_v0.mp4`

## How to open

```text
# re-run capture
py scripts/run_mkm_domain_a_hold_auto_demo_capture_v0.py

# or open flipbook after capture
start reports/domain_a_demo_shots/flipbook.html
```

## Gallery

![01_ui_pass.png](../../../reports/domain_a_demo_shots/01_ui_pass.png)
![02_ui_hold.png](../../../reports/domain_a_demo_shots/02_ui_hold.png)
![03_audit_api.png](../../../reports/domain_a_demo_shots/03_audit_api.png)
![04_cli_synthetic_sop.png](../../../reports/domain_a_demo_shots/04_cli_synthetic_sop.png)

## Still needs human

- Loom 계정 로그인·클라우드 업로드
- 보이스오버 나레이션
- 공개 SaaS URL (없음 → cold outbound는 여전히 DO_NOT_SEND 가능)

## Verdict impact (honest)

| Audience | Impact |
|----------|--------|
| Friend soft | 개선 가능 — 로컬 flipbook/mp4 공유 가능 |
| Cold outbound | 여전히 **DO_NOT_SEND** 가능 — 공개 URL·Loom 없음, SEND HOLD |

## Walls

- 스크린샷 ≠ 라이브 멀티유저 SaaS
- auto capture ≠ Loom upload
- smoke_ok=True · synth_cli_exit=0
