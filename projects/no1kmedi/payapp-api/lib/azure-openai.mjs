/**
 * Azure OpenAI helpers (payapp-api / api.no1kmedi.com).
 * Mirrors projects/no1kmedi/src/lib/azure-openai-config.ts
 */

export function getAzureOpenAiConfig() {
  const endpoint = String(process.env.AZURE_OPENAI_ENDPOINT || "")
    .trim()
    .replace(/\/$/, "");
  const apiKey = String(process.env.AZURE_OPENAI_API_KEY || "").trim();
  const deployment = String(
    process.env.AZURE_OPENAI_DEPLOYMENT || process.env.AZURE_OPENAI_DEPLOYMENT_NAME || ""
  ).trim();
  if (!endpoint || !apiKey || !deployment) return null;
  const apiVersion = String(process.env.AZURE_OPENAI_API_VERSION || "2024-08-01-preview").trim();
  return { endpoint, apiKey, deployment, apiVersion };
}

export function isAzureOpenAiConfigured() {
  return getAzureOpenAiConfig() !== null;
}

export function azureOpenAiChatCompletionsUrl(cfg) {
  const dep = encodeURIComponent(cfg.deployment);
  const ver = encodeURIComponent(cfg.apiVersion);
  return `${cfg.endpoint}/openai/deployments/${dep}/chat/completions?api-version=${ver}`;
}

export function azureOpenAiFetchTimeoutMs() {
  const v = parseInt(String(process.env.AZURE_OPENAI_FETCH_TIMEOUT_MS || ""), 10);
  if (Number.isFinite(v) && v >= 5000) return Math.min(v, 180000);
  return 60000;
}

export function mkmHybridUsesAzureFirst() {
  const raw = String(process.env.MKM_LLM_PRIORITY || process.env.JEMA_AI_LLM_PRIORITY || "")
    .trim()
    .toLowerCase();
  if (raw === "azure_only" || raw === "azure_first") return true;
  if (raw && raw !== "auto") return false;
  return isAzureOpenAiConfigured();
}
