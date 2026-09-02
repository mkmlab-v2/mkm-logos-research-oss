import type { LogosReasoningPathV1, LogosRouterPathV1 } from "./logosResearchHighlightV1";

export type LogosStudioPresetGuardPreset = {
  id: string;
  prompt_ko: string;
  keywords?: string[];
  router_path_v1?: LogosRouterPathV1;
};

export type LogosPresetGuardAction = "aligned" | "auto_route";

export type LogosPresetQueryGuardV1 = {
  action: LogosPresetGuardAction;
  requested_preset_id: string;
  routed_preset_id: string;
  message_ko: string;
};

const STRONG_QUERY_MATCHES = new Set(["text", "lexical", "embedding"]);

function normalizeQueryText(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function scoreQueryPresetAlignment(preset: LogosStudioPresetGuardPreset, query: string): number {
  const q = normalizeQueryText(query);
  if (!q) return 99;

  const prompt = normalizeQueryText(preset.prompt_ko);
  let score = 0;

  if (prompt.includes(q) || q.includes(prompt.slice(0, Math.min(24, prompt.length)))) {
    score += 3;
  }
  for (const token of q.split(" ")) {
    if (token.length >= 2 && prompt.includes(token)) score += 1;
  }
  for (const rawKw of preset.keywords ?? []) {
    const kw = normalizeQueryText(rawKw);
    if (kw.length >= 2 && q.includes(kw)) score += 2;
    for (const token of q.split(" ")) {
      if (token.length >= 2 && kw.includes(token)) score += 1;
    }
  }
  return score;
}

export function queryAlignsWithPreset(preset: LogosStudioPresetGuardPreset, query: string): boolean {
  return scoreQueryPresetAlignment(preset, query) >= 2;
}

export function buildPresetQueryGuardMessage(
  requested: LogosStudioPresetGuardPreset,
  routed: LogosStudioPresetGuardPreset,
): string {
  return `[HYPO] 선택 프리셋「${labelForPreset(requested)}」과 질의 주제가 달라 spine을「${labelForPreset(routed)}」(으)로 자동 전환했습니다. research_only · NON_GATING.`;
}

function labelForPreset(preset: LogosStudioPresetGuardPreset): string {
  const prompt = preset.prompt_ko.trim();
  return prompt.length > 48 ? `${prompt.slice(0, 48)}…` : prompt;
}

export function isStrongQueryPresetMatch(match: string): boolean {
  return STRONG_QUERY_MATCHES.has(match);
}

export function applyPresetQueryGuard(args: {
  presets: LogosStudioPresetGuardPreset[];
  requestedPresetId: string;
  query: string;
  queryRoutedPresetId: string | null;
  queryMatch: string;
}): { preset_id: string; preset_guard: LogosPresetQueryGuardV1 | null; match: string } {
  const requested = args.presets.find((p) => p.id === args.requestedPresetId);
  if (!requested) {
    return { preset_id: args.requestedPresetId, preset_guard: null, match: "id" };
  }

  if (queryAlignsWithPreset(requested, args.query)) {
    return {
      preset_id: args.requestedPresetId,
      preset_guard: {
        action: "aligned",
        requested_preset_id: args.requestedPresetId,
        routed_preset_id: args.requestedPresetId,
        message_ko: "",
      },
      match: "id",
    };
  }

  const routedId = args.queryRoutedPresetId;
  if (
    routedId &&
    routedId !== args.requestedPresetId &&
    isStrongQueryPresetMatch(args.queryMatch)
  ) {
    const routed = args.presets.find((p) => p.id === routedId);
    if (routed) {
      return {
        preset_id: routedId,
        preset_guard: {
          action: "auto_route",
          requested_preset_id: args.requestedPresetId,
          routed_preset_id: routedId,
          message_ko: buildPresetQueryGuardMessage(requested, routed),
        },
        match: `query_guard_${args.queryMatch}`,
      };
    }
  }

  return { preset_id: args.requestedPresetId, preset_guard: null, match: "id" };
}
