$ErrorActionPreference = "Stop"

# Single hub: C:\workspace\.env (gitignored). Non-empty values are copied to Windows User env
# so scheduled tasks and new shells see the same keys. Keys not in .env or left empty are skipped.
$envFile = "C:\workspace\.env"

$keys = @(
  # Trading / exchange
  "BINANCE_API_KEY",
  "BINANCE_API_SECRET",
  "OHLC_BAR_INTERVAL_SEC",
  "OHLC_MIN_COMPLETED_BARS",
  # Showroom / public events
  "PUBLIC_EVENT_BRIDGE_WEBHOOK_URL",
  "PUBLIC_EVENT_BRIDGE_TOKEN",
  "PUBLIC_EVENT_GATEWAY_TOKEN",
  "PUBLIC_EVENT_BRIDGE_ENABLED",
  "SHOWROOM_INGEST_URL",
  # Public event gateway (local MVP)
  "PUBLIC_EVENT_GATEWAY_HOST",
  "PUBLIC_EVENT_GATEWAY_PORT",
  "PUBLIC_EVENT_GATEWAY_ALLOW_ORIGIN",
  "PUBLIC_EVENT_GATEWAY_WORKSPACE_ROOT",
  "PUBLIC_EVENT_GATEWAY_STATE_PATH",
  # N8N / OPS alarms
  "N8N_ALL_GREEN_WEBHOOK_URL",
  "N8N_WEBHOOK_URL",
  "OPS_ALARM_WEBHOOK_URL",
  "COMPRESSION_KPI_ALARM_WEBHOOK_URL",
  # Slack (multiple channels / fallbacks)
  "SLACK_WEBHOOK_URL",
  "FACT_SAFE_SLACK_WEBHOOK_URL",
  "FACT_SAFE_FATAL_SLACK_WEBHOOK",
  "ALL_GREEN_SLACK_WEBHOOK_URL",
  "ALL_GREEN_STALE_SLACK_WEBHOOK_URL",
  "ALL_GREEN_SLACK_LIVE",
  "A_TRACK_SLACK_WEBHOOK_URL",
  "NIGHT_WATCHMAN_WEBHOOK_URL",
  # Telegram
  "TELEGRAM_BOT_TOKEN",
  "TELEGRAM_CHAT_ID",
  "TELEGRAM_ALERT_MODE",
  "OPS_TELEGRAM_FALLBACK_ENABLED",
  "TELEGRAM_TRADE_ALERT_COOLDOWN_SECONDS",
  "TELEGRAM_TRADE_ALERT_PRICE_BAND_BPS",
  # Google AI / Gemini
  "GEMINI_API_KEY",
  "GOOGLE_API_KEY",
  # B-track OpenClaude / OpenAI-compatible
  "OPENCLAUDE_PILOT_API_KEY",
  "OPENCLAUDE_PILOT_OPENAI_BASE_URL",
  "OPENCLAUDE_PILOT_OPENAI_MODEL",
  # Bluesky / ATProto
  "BSKY_HANDLE",
  "BSKY_EMAIL",
  "BSKY_IDENTIFIER",
  "BSKY_APP_PASSWORD",
  "BLUESKY_HANDLE",
  "BLUESKY_EMAIL",
  "BLUESKY_APP_PASSWORD",
  # Paths (override defaults in scripts)
  "WORKSPACE_ROOT",
  "WORKSPACE",
  "MEMORY_ROOT",
  "MKM_MEMORY_REPORT_DIR",
  "MKM_VAULT_ROOT",
  "L2_SHADOW_OUT_DIR",
  # Risk profile (daemon / OPS)
  "RISK_PROFILE_SOURCE_NAME",
  "RISK_PROFILE_MODE_NAME",
  "RISK_PROFILE_MAX_AGE_MINUTES",
  # PocketBase
  "POCKETBASE_URL",
  "POCKETBASE_AUTH_TOKEN",
  # Market / news APIs
  "NEWSAPI_KEY",
  "ALPHA_VANTAGE_API_KEY",
  "FRED_API_KEY",
  # Hostinger MCP / API
  "HOSTINGER_API_TOKEN",
  "API_TOKEN",
  # Cloudflare API (DNS ensure / token verify; SSOT = workspace .env → sync to User)
  "CLOUDFLARE_API_TOKEN",
  "CF_API_TOKEN",
  "CLOUDFLARE_ZONE_ID",
  # Kakao
  "KAKAO_REST_API_KEY",
  "KAKAO_ADMIN_KEY",
  "KAKAO_CHANNEL_UUID",
  "KAKAO_JAVASCRIPT_KEY",
  "VITE_KAKAO_REST_API_KEY",
  "VITE_KAKAO_JAVASCRIPT_KEY",
  # Execute guard (v2)
  "EXECUTE_APPROVAL_HMAC_KEY",
  # VPS SSH helpers
  "MKM_VPS_HOST",
  "MKM_VPS_USER",
  "JEMAAI_VPS_SHOWROOM_ROOT",
  "JEMAAI_VPS_RELOAD_NGINX",
  "MKM_VPS_SCP_EXTRA_ARGS",
  # Pixel / CDN
  "PIXEL_BATTALION_BASE_URL",
  # Strategy / gates (optional)
  "DUAL_REGIME_GATE_PROFILE",
  "AND_GATE_MODE",
  "LOGOS_TIMELINE_TRADITION",
  "OMNI_ORACLE_STATE_TRANSITION_URL",
  # OPS local LLM
  "OPS_LOCAL_LLM_ROLLOUT_MODE",
  "OPS_LOCAL_LLM_CANARY_GATE_PATH",
  # Local Ollama (optional; tools / local engine default)
  "OLLAMA_MODEL",
  "OLLAMA_HOST",
  # Fact-safe monthly / eval (run_waiting_queue_monthly_check.ps1)
  "FACT_SAFE_INPUT_USD_PER_1K_TOKENS",
  "FACT_SAFE_OUTPUT_USD_PER_1K_TOKENS",
  "FACT_SAFE_ENABLE_HIGH_SAMPLE_VLLM_EVAL",
  "FACT_SAFE_HIGH_SAMPLE_CASES",
  "FACT_SAFE_HIGH_SAMPLE_RUNS",
  "FACT_SAFE_OVERRIDE_SKEW_STREAK_THRESHOLD",
  # Daily waiting-queue batch overrides
  "DAILY_CLOSE_INPUT_JSON_PATH",
  "DAILY_BTC_BINANCE_D1_RETURN_PCT",
  "DAILY_KOSPI_D1_RETURN_PCT",
  "DAILY_REQUIRE_CLOSE_RETURN",
  "DAILY_PENDING_CLOSE_ALERT_STREAK",
  # Memory inventory (run_workspace_automation_health.ps1)
  "MKM_MEMORY_INVENTORY_FULL",
  "MKM_MEMORY_INVENTORY_MAX_FILES",
  # Symbol lane
  "SYMBOL_C_RETENTION_ENV",
  "SYMBOL_C_RETENTION_DRY_RUN",
  # Billing (optional)
  "FACT_SAFE_BILLING_INVOICE_OUT"
)

if (-not (Test-Path -LiteralPath $envFile)) {
  throw "Missing .env file: $envFile"
}

$map = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#") -or $line.IndexOf("=") -lt 1) {
    return
  }
  $idx = $line.IndexOf("=")
  $k = $line.Substring(0, $idx).Trim()
  $v = $line.Substring($idx + 1)
  $map[$k] = $v
}

foreach ($k in $keys) {
  if ($map.ContainsKey($k) -and -not [string]::IsNullOrWhiteSpace($map[$k])) {
    [Environment]::SetEnvironmentVariable($k, $map[$k], "User")
    Write-Host "SET_USER:$k"
  }
  else {
    Write-Host "SKIP_MISSING_IN_DOTENV:$k"
  }
}

function Get-DotenvVal([string]$key) {
  if ($map.ContainsKey($key) -and -not [string]::IsNullOrWhiteSpace($map[$key])) {
    return $map[$key].Trim()
  }
  return $null
}

# Cloudflare: scripts prefer CLOUDFLARE_API_TOKEN; allow CF_API_TOKEN-only in .env.
$cfMain = Get-DotenvVal "CLOUDFLARE_API_TOKEN"
$cfAlt = Get-DotenvVal "CF_API_TOKEN"
if ([string]::IsNullOrWhiteSpace($cfMain) -and -not [string]::IsNullOrWhiteSpace($cfAlt)) {
  [Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", $cfAlt, "User")
  Write-Host "SET_USER:CLOUDFLARE_API_TOKEN (mirrored from CF_API_TOKEN)"
}

# Bluesky / ATProto: scheduled tasks and some paths expect User-scope BSKY_*.
# Mirror from BLUESKY_* when BSKY_* is absent in .env (same value, canonical name).
$bskyH = Get-DotenvVal "BSKY_HANDLE"
if (-not $bskyH) { $bskyH = Get-DotenvVal "BLUESKY_HANDLE" }
$bskyP = Get-DotenvVal "BSKY_APP_PASSWORD"
if (-not $bskyP) { $bskyP = Get-DotenvVal "BLUESKY_APP_PASSWORD" }
if (-not [string]::IsNullOrWhiteSpace($bskyH)) {
  [Environment]::SetEnvironmentVariable("BSKY_HANDLE", $bskyH, "User")
  if (-not (Get-DotenvVal "BSKY_HANDLE")) {
    Write-Host "SET_USER:BSKY_HANDLE (mirrored from BLUESKY_HANDLE)"
  }
}
if (-not [string]::IsNullOrWhiteSpace($bskyP)) {
  [Environment]::SetEnvironmentVariable("BSKY_APP_PASSWORD", $bskyP, "User")
  if (-not (Get-DotenvVal "BSKY_APP_PASSWORD")) {
    Write-Host "SET_USER:BSKY_APP_PASSWORD (mirrored from BLUESKY_APP_PASSWORD)"
  }
}

$opsAlarmCur = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "User")
if ([string]::IsNullOrWhiteSpace($opsAlarmCur)) {
  $mirror = $null
  if ($map.ContainsKey("N8N_WEBHOOK_URL") -and -not [string]::IsNullOrWhiteSpace($map["N8N_WEBHOOK_URL"])) {
    $mirror = $map["N8N_WEBHOOK_URL"].Trim()
  }
  if ([string]::IsNullOrWhiteSpace($mirror)) {
    $mirror = [Environment]::GetEnvironmentVariable("N8N_WEBHOOK_URL", "User")
  }
  if (-not [string]::IsNullOrWhiteSpace($mirror)) {
    [Environment]::SetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", $mirror, "User")
    Write-Host "MIRROR_USER:OPS_ALARM_WEBHOOK_URL<=N8N_WEBHOOK_URL"
  }
}

$compAlarmCur = [Environment]::GetEnvironmentVariable("COMPRESSION_KPI_ALARM_WEBHOOK_URL", "User")
if ([string]::IsNullOrWhiteSpace($compAlarmCur)) {
  $mirrorOps = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "User")
  if (-not [string]::IsNullOrWhiteSpace($mirrorOps)) {
    [Environment]::SetEnvironmentVariable("COMPRESSION_KPI_ALARM_WEBHOOK_URL", $mirrorOps, "User")
    Write-Host "MIRROR_USER:COMPRESSION_KPI_ALARM_WEBHOOK_URL<=OPS_ALARM_WEBHOOK_URL"
  }
}

$fatalSlackCur = [Environment]::GetEnvironmentVariable("FACT_SAFE_FATAL_SLACK_WEBHOOK", "User")
if ([string]::IsNullOrWhiteSpace($fatalSlackCur)) {
  $mirrorSlack = $null
  if ($map.ContainsKey("SLACK_WEBHOOK_URL") -and -not [string]::IsNullOrWhiteSpace($map["SLACK_WEBHOOK_URL"])) {
    $mirrorSlack = $map["SLACK_WEBHOOK_URL"].Trim()
  }
  if ([string]::IsNullOrWhiteSpace($mirrorSlack)) {
    $mirrorSlack = [Environment]::GetEnvironmentVariable("SLACK_WEBHOOK_URL", "User")
  }
  if (-not [string]::IsNullOrWhiteSpace($mirrorSlack)) {
    [Environment]::SetEnvironmentVariable("FACT_SAFE_FATAL_SLACK_WEBHOOK", $mirrorSlack, "User")
    Write-Host "MIRROR_USER:FACT_SAFE_FATAL_SLACK_WEBHOOK<=SLACK_WEBHOOK_URL"
  }
}

foreach ($k in $keys) {
  $uv = [Environment]::GetEnvironmentVariable($k, "User")
  if ([string]::IsNullOrWhiteSpace($uv)) {
    Write-Host "USER_MISSING:$k"
  }
  else {
    Write-Host "USER_OK:$k"
  }
}
