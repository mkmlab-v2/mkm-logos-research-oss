# mkm-logos-research-oss

![OSS smoke](https://github.com/mkmlab-v2/mkm-logos-research-oss/actions/workflows/oss-smoke.yml/badge.svg)

**Logos Research open-core harness** — offline conflict retrieval + synthesis gates (fixture-only).

| What | Where |
|------|--------|
| **Product beta (Q&A UI)** | [logos.jema-ai.com/logos-research/ask](https://logos.jema-ai.com/logos-research/ask) |
| **~60s clone repro** | below |
| **Feedback** | [Issues · beta_feedback](https://github.com/mkmlab-v2/mkm-logos-research-oss/issues/new?template=beta_feedback.yml) |
| **Third-party repro** | [Discussion #4](https://github.com/mkmlab-v2/mkm-logos-research-oss/discussions/4) |

**Not in this repo:** KRV full text · full Gnosis morphology · Next.js app · trading weights · payment UI.

`research_only` · `send_gate: HOLD` · `[NON_GATING]`

## Quickstart (fixture-only)

```bash
git clone https://github.com/mkmlab-v2/mkm-logos-research-oss.git
cd mkm-logos-research-oss
pip install -r requirements.txt
py scripts/run_logos_oss_premarket_smoke_v1.py
```

Expect **exit code 0** (ingest → conflict gates → lemma bridge → pytest → manifest verify).

## Scope

- Ships: harness scripts, Gnosis **fixture sample**, conflict surface JSON, pytest gates, beta contract pointer.
- You provide locally (optional): full Gnosis export (CC-BY-SA 4.0), KRV citation corpus — see `data/logos/gnosis_kg/README.md`.

## License

MIT — see `LICENSE`. Harness outputs are `[HYPO]` / B-track reference only.
