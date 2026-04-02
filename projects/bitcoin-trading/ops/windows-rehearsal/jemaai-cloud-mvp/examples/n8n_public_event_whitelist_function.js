// n8n Function node template: public-event.v1 whitelist + character id normalization
// Apply: n8n → open workflow → Function node → replace code with this file → wire to HTTP Request POST https://api.jemaai.cloud/api/public-events/ingest (header X-Public-Event-Token).
// Input: item.json (raw internal payload)
// Output: sanitized payload only (safe for POST /api/public-events/ingest)

const allowedCharacterIds = new Set([
  "rat_arbitrage",
  "ox_guard",
  "tiger_shield",
  "rabbit_scalper",
  "dragon_quant",
  "snake_hedger",
  "horse_trend",
  "sheep_yield",
  "monkey_momentum",
  "rooster_oracle",
  "dog_sentinel",
  "pig_accumulator",
  "demo_guard",
  "unknown_guard",
  "bull_alpha",
  "bear_shield"
]);

function normalizeCharacterId(raw) {
  const cid = String(raw || "").trim().toLowerCase();
  if (!cid) return "unknown_guard";
  if (allowedCharacterIds.has(cid)) return cid;
  if (cid.includes("bull") || cid.includes("attack")) return "bull_alpha";
  if (cid.includes("bear") || cid.includes("shield") || cid.includes("guard")) return "bear_shield";
  return "unknown_guard";
}

function safeRiskLevel(raw) {
  const v = String(raw || "").trim().toUpperCase();
  if (v === "SAFE" || v === "WARNING") return v;
  return "WARNING";
}

const src = items[0].json || {};
const now = new Date().toISOString();
const delaySec = Number(src.delay_seconds ?? src?.delayed_metrics?.delay_seconds ?? 180);
const normalizedDelay = Number.isFinite(delaySec) ? Math.min(300, Math.max(120, Math.round(delaySec))) : 180;

const out = {
  timestamp: String(src.timestamp || now),
  active_character_id: normalizeCharacterId(src.active_character_id),
  risk_level: safeRiskLevel(src.risk_level),
  public_signal_direction: String(src.public_signal_direction || "HOLD").toUpperCase(),
  abstract_reason: String(src.abstract_reason || "Public showroom sanitized event."),
  schema_version: "public-event.v1",
  event_id: String(src.event_id || `n8n-${Date.now()}`),
  source: String(src.source || "n8n_bridge_whitelist"),
  system_status: String(src.system_status || "online"),
  active_strategies_count: Number(src.active_strategies_count ?? 0),
  delayed_metrics: {
    delay_seconds: normalizedDelay,
    pnl_pct_vs_start: Number(src?.delayed_metrics?.pnl_pct_vs_start ?? 0),
    as_of_utc: String(src?.delayed_metrics?.as_of_utc || now)
  },
  direction_abstract: String(src.direction_abstract || "flat").toLowerCase(),
  disclaimer_ref: "jemaai_showroom_v1",
  last_ok_utc: String(src.last_ok_utc || now)
};

return [{ json: out }];
