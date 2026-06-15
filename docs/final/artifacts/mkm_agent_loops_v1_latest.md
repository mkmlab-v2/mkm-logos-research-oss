# MKM Agent Micro-Loops v1

**SSOT:** copy-paste kickoffs for Cursor / Claude Code chat loops.  
**Routine / persona:** `powershell -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona MkmAgentLoops` → `reports/mkm_agent_loops_routine_v1_latest.json`  
**Inspiration:** [loops.elorm.xyz](https://loops.elorm.xyz/) (Goal · Max iterations · Between-iterations check · Exit when).  
**Fact-Lock:** pass/fail = runnable script exit code + artifact path — not chat narrative.

## MKM guardrails (all loops)

- **NEVER** auto-promote Track B → Track A, live trade, `apply-active`, or SEND without human gate.
- **NEVER** bypass ECC on high-risk paths — prefer `py scripts/athena_run_v1.py -- <child>` when CONSTITUTION §28 applies.
- **NEVER** treat NotebookLM / chat summary as implementation proof.
- **Done** = exit code 0 + artifact/log path + reproducible command.
- Repo root: `C:\workspace` · Windows: use `py` and `powershell -NoProfile -ExecutionPolicy Bypass -File …`.

---

## 1. P0 Until Green

**When:** after SSOT / CONSTITUTION path edits, or before merge.  
**Persona shortcut:** `Invoke-MkmPersonaHealth_v1.ps1 -Persona P0`

### Kickoff (copy)

```
Start the "P0 Until Green" loop.

Goal: scripts/verify_p0_constitution_gate_paths.ps1 exits 0 (all required paths exist).

Max iterations: 6

Between iterations run:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_p0_constitution_gate_paths.ps1

Exit when: the P0 script exits 0.

Step 1: Run P0 paths gate. On failure, fix the first missing path or stale CONSTITUTION pointer (scripts + pytest only — no prose-only "fixed"). Re-run until green.

Self-pace this loop. After each iteration, run the check command, read stdout/stderr, and only continue if the exit condition is not met. Stop when exit passes or max iterations is reached. Give a one-line status each pass.

Fact-Lock footer on stop: command · exit code · first failing path (if any).
```

---

## 2. Bounded Lane Shadow Until Pass

**When:** infra/ms/oracle/design lane smoke after pin or whitelist changes.  
**SSOT:** CONSTITUTION §1.4.1 · `reports/bounded_lane_loop_v1_latest.json`  
**Persona shortcut:** `Invoke-MkmPersonaHealth_v1.ps1 -Persona BoundedLaneLoopShadow`

### Kickoff (copy)

```
Start the "Bounded Lane Shadow Until Pass" loop.

Goal: bounded lane loop dry-run for lane=infra yields outcome_class shadow_pass (NOT Track A promotion).

Max iterations: 4

Between iterations run:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BoundedLaneLoop_v1.ps1 -Lane infra -DryRun

Exit when: Invoke-BoundedLaneLoop exits 0 AND reports/bounded_lane_loop_v1_latest.json has "outcome_class": "shadow_pass".

Step 1: Run dry-run invoke. If shadow_reject or shadow_warning, read reports/bounded_lane_loop_audit.jsonl, fix whitelist/pin/resume-pack issue with minimal diff, repeat. Do NOT enqueue todo_queue, push, or live paths.

Self-pace this loop. Stop at shadow_pass or max iterations. One-line status each pass.

Fact-Lock footer: invoke exit code · outcome_class · reports/bounded_lane_loop_v1_latest.json path.
```

**Lane swap:** replace `-Lane infra` with `ms` | `oracle` | `design` as needed.

---

## 3. Parallel Passive Until OK

**When:** daily passive observation (shim · L1 · MAX_HYPO). Single mechanical pass — re-run only if a lane failed.  
**SSOT:** `reports/parallel_passive_loop_v1_latest.json` · rule `@parallel-passive-loop-v1`

### Kickoff (copy)

```
Start the "Parallel Passive Until OK" loop.

Goal: parallel passive loop completes with exit 0 (3-lane default; D/web_ops OFF unless GPU approved).

Max iterations: 2

Between iterations run:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ParallelPassiveLoop_v1.ps1

Exit when: Invoke-ParallelPassiveLoop exits 0 AND reports/parallel_passive_loop_v1_latest.json shows all included lanes ok.

Step 1: Run 3-lane passive loop. On failure, read the failing lane in the JSON report, fix root cause (shadow/B-track only), re-run once. Do NOT IncludeWebOps, apply-active, live ON, or MS headline merge.

Self-pace this loop. One-line status each pass.

Fact-Lock footer: exit code · reports/parallel_passive_loop_v1_latest.json · lanes run.
```

---

## 4. CI Failure Watcher (interval)

**When:** branch has open PR or you pushed and waiting for GitHub checks.  
**Requires:** `gh` authenticated · branch tracks remote.

### Kickoff (copy — Cursor `/loop`)

```
/loop 5m

Start the "CI Failure Watcher" loop.

Goal: latest GitHub Actions run on the current branch has conclusion success.

Max iterations: 12

Between iterations run:
gh run list --branch (git branch --show-current) --limit 1 --json conclusion,status,url -q ".[0]"

Exit when: latest run conclusion is "success".

Step 1: Poll CI. If failed or cancelled, run: gh run view <run-id> --log-failed (or gh run view --log). Reproduce locally (pytest or the failing workflow step), fix minimal root cause, commit only if user asked, push if needed, then wait for next poll.

Self-pace this loop. Do NOT force-push main. One-line status each pass (conclusion + URL).

Fact-Lock footer: gh conclusion · run URL · local repro command · exit code.
```

**Local-first variant (no push):** replace exit when with local `pytest <failing-test> -q` exits 0 after reproducing CI failure.

---

## 5. De-Sloppify Pass (MKM)

**When:** after implementation, before commit/PR.  
**Aligns with:** min-change rule · context diet · ce-code-review residuals.

### Kickoff (copy)

```
Start the "De-Sloppify Pass" loop.

Goal: recent diff is minimal, convention-aligned, and context-diet + targeted tests pass.

Max iterations: 4

Between iterations run:
py scripts/check_cursor_rules_context_diet_v1.py --strict

Exit when: context diet exits 0 AND (if code changed) the smallest relevant pytest slice for the diff exits 0 AND review finds no debug/dead-branch/drive-by refactor slop.

Step 1: Review git diff. Remove debug prints, commented-out blocks, unrelated edits. Match surrounding naming and patterns. Run context diet strict; add/fix only the pytest files touched by the change (e.g. py -m pytest tests/test_<module>_v1.py -q). No new Markdown unless user asked.

Self-pace this loop. One-line status each pass.

Fact-Lock footer: diet exit code · pytest command + exit code · files changed count.
```

**Heavier gate (pre-merge):** swap diet-only check for  
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipTwoTrackSubmissionAndMultiSymbolSmoke -SkipAramaicBtrackGraphPipelineSmoke`  
only when the change touches CONSTITUTION-critical paths.

---

## Quick reference

| Loop | Check command | Exit artifact |
|------|---------------|---------------|
| P0 Until Green | `verify_p0_constitution_gate_paths.ps1` | exit 0 |
| Bounded Lane Shadow | `Invoke-BoundedLaneLoop_v1.ps1 -DryRun` | `bounded_lane_loop_v1_latest.json` → `shadow_pass` |
| Parallel Passive | `Invoke-ParallelPassiveLoop_v1.ps1` | `parallel_passive_loop_v1_latest.json` |
| CI Failure Watcher | `gh run list …` | conclusion `success` |
| De-Sloppify | `check_cursor_rules_context_diet_v1.py --strict` + pytest slice | exit 0 |

**Related macro-loops (not chat micro-loops):** `run_fact_lock_bundle.ps1` · persona `AthenaBundle` · bounded lane weekly tasks · CONSTITUTION §1.4.
