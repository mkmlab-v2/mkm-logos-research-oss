/**
 * Golden-style checks for LLM priority resolution (no network).
 *
 * Run (pick one):
 * - cwd = projects/no1kmedi: npm run smoke:guardian-llm-priority
 * - cwd = workspace root: npm run smoke:guardian-llm-priority --prefix projects/no1kmedi
 * - direct: node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --experimental-strip-types ./scripts/smoke-guardian-llm-priority.mts
 *
 * .mts = ESM without --experimental-default-type=module (unsupported on some Node builds).
 */

import { resolveLlmPriorityForCaller } from "../src/lib/ai-provider.ts";

const ISOLATED_ENV_KEYS = [
  "GUARDIAN_CHAT_LLM_PRIORITY",
  "JEMA_AI_LLM_PRIORITY",
  "GEMINI_API_KEY",
  "GOOGLE_API_KEY",
  "OPENROUTER_API_KEY",
  "OLLAMA_HOST",
  "LOCAL_LLM_URL",
] as const;

type Case = { name: string; env: Partial<Record<(typeof ISOLATED_ENV_KEYS)[number], string | undefined>>; want: ReturnType<typeof resolveLlmPriorityForCaller> };

function runCase(c: Case) {
  const prev: Record<string, string | undefined> = {};
  for (const k of ISOLATED_ENV_KEYS) {
    prev[k] = process.env[k];
    delete process.env[k];
  }
  for (const [k, v] of Object.entries(c.env)) {
    if (v === undefined) continue;
    process.env[k] = v;
  }
  try {
    const got = resolveLlmPriorityForCaller("guardian_public_chat");
    if (got !== c.want) {
      console.error(`FAIL: ${c.name}\n  want=${c.want} got=${got}`);
      process.exitCode = 1;
    } else {
      console.log(`ok: ${c.name} -> ${got}`);
    }
  } finally {
    for (const k of ISOLATED_ENV_KEYS) {
      if (prev[k] === undefined) delete process.env[k];
      else process.env[k] = prev[k]!;
    }
  }
}

const cases: Case[] = [
  {
    name: "explicit GUARDIAN overrides to openrouter_first",
    env: {
      GUARDIAN_CHAT_LLM_PRIORITY: "openrouter_first",
      JEMA_AI_LLM_PRIORITY: "local_only",
      OPENROUTER_API_KEY: "k",
      OLLAMA_HOST: "http://127.0.0.1:11434",
    },
    want: "openrouter_first",
  },
  {
    name: "both backends no guardian env -> local_first (no gemini key)",
    env: {
      JEMA_AI_LLM_PRIORITY: "auto",
      OPENROUTER_API_KEY: "sk-test",
      OLLAMA_HOST: "http://127.0.0.1:11434",
    },
    want: "local_first",
  },
  {
    name: "local only no key -> local_only (no gemini key)",
    env: {
      OLLAMA_HOST: "http://127.0.0.1:11434",
    },
    want: "local_only",
  },
  {
    name: "no local inherits JEMA local_first (no gemini key)",
    env: {
      OPENROUTER_API_KEY: "k",
      JEMA_AI_LLM_PRIORITY: "local_first",
    },
    want: "local_first",
  },
  {
    name: "no local inherits JEMA auto (no gemini key)",
    env: {
      OPENROUTER_API_KEY: "k",
      JEMA_AI_LLM_PRIORITY: "auto",
    },
    want: "auto",
  },
  {
    name: "gemini key present no explicit guardian -> gemini_first",
    env: {
      GEMINI_API_KEY: "gk-test",
      JEMA_AI_LLM_PRIORITY: "auto",
      OPENROUTER_API_KEY: "sk-test",
      OLLAMA_HOST: "http://127.0.0.1:11434",
    },
    want: "gemini_first",
  },
];

for (const c of cases) runCase(c);

if (process.exitCode === 1) {
  console.error("[smoke-guardian-llm-priority] one or more cases failed");
  process.exit(1);
}
console.log("[smoke-guardian-llm-priority] all cases passed");
