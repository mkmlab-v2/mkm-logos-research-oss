/**
 * Azure OpenAI (Microsoft for Startups credits) — OpenAI-compatible chat/completions.
 * SSOT env: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT.
 */

export type AzureOpenAiConfig = {
  endpoint: string;
  apiKey: string;
  deployment: string;
  apiVersion: string;
};

export function getAzureOpenAiConfig(): AzureOpenAiConfig | null {
  const endpoint = (process.env.AZURE_OPENAI_ENDPOINT || "").trim().replace(/\/$/, "");
  const apiKey = (process.env.AZURE_OPENAI_API_KEY || "").trim();
  const deployment = (
    process.env.AZURE_OPENAI_DEPLOYMENT || process.env.AZURE_OPENAI_DEPLOYMENT_NAME || ""
  ).trim();
  if (!endpoint || !apiKey || !deployment) return null;
  const apiVersion = (process.env.AZURE_OPENAI_API_VERSION || "2024-08-01-preview").trim();
  return { endpoint, apiKey, deployment, apiVersion };
}

export function isAzureOpenAiConfigured(): boolean {
  return getAzureOpenAiConfig() !== null;
}

export function azureOpenAiChatCompletionsUrl(cfg: AzureOpenAiConfig): string {
  const dep = encodeURIComponent(cfg.deployment);
  const ver = encodeURIComponent(cfg.apiVersion);
  return `${cfg.endpoint}/openai/deployments/${dep}/chat/completions?api-version=${ver}`;
}

export function azureOpenAiDeploymentModel(cfg?: AzureOpenAiConfig | null): string {
  const c = cfg ?? getAzureOpenAiConfig();
  return c?.deployment || "gpt-4o-mini";
}

export function azureOpenAiFetchTimeoutMs(): number {
  const v = parseInt(process.env.AZURE_OPENAI_FETCH_TIMEOUT_MS || "", 10);
  if (Number.isFinite(v) && v >= 5000) return Math.min(v, 180000);
  return 60000;
}

/** Global MKM LLM priority (all product domains). */
export function resolveMkmLlmPriorityRaw(): string {
  return (process.env.MKM_LLM_PRIORITY || process.env.JEMA_AI_LLM_PRIORITY || "").trim();
}

export function mkmLlmDefaultsToAzureFirst(): boolean {
  const raw = resolveMkmLlmPriorityRaw().toLowerCase();
  if (raw === "azure_first" || raw === "azure_only") return true;
  if (raw && raw !== "auto") return false;
  return isAzureOpenAiConfigured();
}
