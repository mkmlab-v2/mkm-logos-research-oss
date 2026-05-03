# Vibe Prompt Set v1 (B-Track BTC First)

## Prompt 1 - Decision Consistency
You are a research-only trading copilot. Analyze BTCUSDT next-day regime and action.

Hard rules:
- Do not output exact price targets.
- **Line 1 of your answer must be exactly** `Final Action: HOLD` **or** `Final Action: REDUCE` **or** `Final Action: WATCH` (nothing before it).
- After line 1, do **not** use the bare tokens HOLD, REDUCE, or WATCH again (paraphrase: e.g. maintain / trim / monitor).
- Use conservative bias if signals conflict; if still ambiguous, line 1 must be `Final Action: HOLD`.
- Include confidence in [0,1] on line 2 as `Confidence: 0.00` (two decimals).

Output format (lines in this order):
1) Final Action: (HOLD|REDUCE|WATCH)
2) Confidence: 0.00-1.00
3) Top 3 reasons
4) Risks

## Prompt 2 - Reproducibility
Given the same BTCUSDT input context, produce a deterministic recommendation with stable structure.

Requirements:
- Keep wording concise.
- Keep decision logic explicit.
- Mention what would flip decision from HOLD to WATCH or REDUCE.

Output format:
- Decision
- Flip conditions
- Missing evidence

## Prompt 3 - Risk-First Lens
Evaluate BTCUSDT with risk-first policy.

Requirements:
- Penalize overfitting and narrative-only signals.
- Separate observed facts vs assumptions.
- If assumptions dominate, choose HOLD.

Output format:
- Facts
- Assumptions
- Action
- Confidence

## Prompt 4 - Shadow Loop Compatibility
Generate a recommendation suitable for shadow-loop evaluation.

Requirements:
- **Line 1** must be exactly `Final Action: HOLD` or `Final Action: REDUCE` or `Final Action: WATCH` (parser uses this line first).
- After line 1, do **not** repeat bare HOLD/REDUCE/WATCH in prose (use paraphrases).
- Line 2: `Confidence: 0.00` (two decimals, 0-1).
- Include a single JSON object (minified or pretty) with keys **exactly**:
  - `decision` (must match line 1: HOLD|REDUCE|WATCH)
  - `confidence` (number 0-1, match line 2)
  - `rationale_short` (one short string)
  - `risk_flags` (array of short strings)

Output format:
1) Line 1–2 as above, then human summary
2) JSON block (one object)

## Execution Protocol
- Run each prompt 10 times.
- Measure decision consistency ratio per prompt.
- Log outputs to `docs/final/artifacts/vibe_runs_raw/` (research only).
- Never auto-promote to Track A.
