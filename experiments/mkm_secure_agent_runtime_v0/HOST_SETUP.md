# MKM Secure Agent Runtime V1.0 — local setup

Development candidate only.

## V1.0 Cursor Agent bridge

V1.0 requires a V0.9 dedicated developer session plus Cursor's live desktop bridge.

The runtime does not create, copy, or migrate Cursor credentials.

Expected bridge discovery root:

```text
%USERPROFILE%\.cursor\desktop-bridge
```

A valid discovery record must match the exact V0.9 session `userDataDir`.

## Agent workflow

1. establish a V0.9 dedicated Cursor session
2. call `cursor_agent_status(session_id)`
3. require:
   `bridge_state = ESTABLISHED`
4. call `cursor_agent_threads(session_id)`
5. choose an exact thread id from that session only
6. call `request_cursor_agent_prompt(...)`
7. approve locally in tray/CLI
8. call `execute_cursor_agent_prompt(...)`

If bridge state is NOT_ESTABLISHED, stop.

## Current test-PC state

Observed:

```text
CURSOR_DESKTOP_BRIDGE_NOT_ESTABLISHED
```

No live Agent prompt was sent.

## V1.0 send policy

Agent prompt submission is treated as an external mutation/SEND-class action.

It requires:
- local privacy ALLOW
- exact session thread
- exact prompt SHA-256 and length
- local HUMAN_GATE
- force=false

## Explicit denials

- force send
- secret / PHI / personal prompt
- git push
- deploy / publish
- mail send
- transfer / bank operation
- destructive directives
- extension install/uninstall

## Regression warning

Latest full branch regression:

```text
95 passed
1 failed
```

Failure is in the existing V0.6 synthetic Edit set-text effect:
expected `fixture-value`, observed `..fixture-value`.

Do not treat V1.0 branch as fully green until that failure is separately adjudicated.

Evidence ceiling:

`BOUNDED_CURSOR_AGENT_WORKER_V1_0_BRIDGE_GATED_CANDIDATE_WITH_REGRESSION_FAIL`
