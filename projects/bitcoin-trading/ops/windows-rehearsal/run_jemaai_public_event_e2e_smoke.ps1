param(
    [string]$ApiBaseUrl = "https://api.jemaai.cloud",
    [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$name, [bool]$ok, [string]$detail) {
    $status = if ($ok) { "PASS" } else { "FAIL" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} - {2}" -f $status, $name, $detail) -ForegroundColor $color
}

function Invoke-JsonGet([string]$url) {
    $r = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec $TimeoutSec
    return ($r.Content | ConvertFrom-Json -ErrorAction Stop)
}

function Invoke-JsonPost([string]$url, [object]$body) {
    $raw = $body | ConvertTo-Json -Depth 8 -Compress
    return Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json" -Body $raw -TimeoutSec $TimeoutSec
}

function Expected-CharacterId([string]$rawId) {
    $id = ""
    if (-not [string]::IsNullOrWhiteSpace($rawId)) {
        $id = $rawId.Trim().ToLowerInvariant()
    }
    $allow = @(
        "rat_arbitrage","ox_guard","tiger_shield","rabbit_scalper",
        "dragon_quant","snake_hedger","horse_trend","sheep_yield",
        "monkey_momentum","rooster_oracle","dog_sentinel","pig_accumulator",
        "demo_guard","unknown_guard","bull_alpha","bear_shield"
    )
    if ([string]::IsNullOrWhiteSpace($id)) { return "unknown_guard" }
    if ($allow -contains $id) { return $id }
    if ($id.Contains("bull") -or $id.Contains("attack")) { return "bull_alpha" }
    if ($id.Contains("bear") -or $id.Contains("shield") -or $id.Contains("guard")) { return "bear_shield" }
    return "unknown_guard"
}

$latestUrl = $ApiBaseUrl.TrimEnd("/") + "/api/public-events/latest"
$ingestUrl = $ApiBaseUrl.TrimEnd("/") + "/api/public-events/ingest"
$profilesUrl = $ApiBaseUrl.TrimEnd("/") + "/character_profiles_v1_1.json"

$results = @()

try {
    $profiles = Invoke-JsonGet -url $profilesUrl
    $profileCount = @($profiles.profiles.PSObject.Properties.Name).Count
    $okProfiles = ($profileCount -ge 16)
    Write-Step "Profiles Endpoint" $okProfiles ("count=" + $profileCount)
    $results += $okProfiles
} catch {
    Write-Step "Profiles Endpoint" $false $_.Exception.Message
    $results += $false
}

$cases = @(
    @{ Name = "whitelist pass"; Input = "dragon_quant" },
    @{ Name = "bull pattern"; Input = "bull_custom_agent" },
    @{ Name = "bear pattern"; Input = "bear_runtime" },
    @{ Name = "unknown fallback"; Input = "non_mapped_id_x" }
)

foreach ($c in $cases) {
    $eventId = "smoke-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $payload = @{
        timestamp = [DateTime]::UtcNow.ToString("o")
        active_character_id = $c.Input
        risk_level = "WARNING"
        public_signal_direction = "HOLD"
        abstract_reason = "e2e smoke " + $c.Name
        schema_version = "public-event.v1"
        event_id = $eventId
        source = "ops_e2e_smoke"
    }

    try {
        $post = Invoke-JsonPost -url $ingestUrl -body $payload
        $latest = Invoke-JsonGet -url $latestUrl
        $expected = Expected-CharacterId -rawId $c.Input
        $ok = ($post.ok -eq $true) -and ($latest.event_id -eq $eventId) -and ($latest.active_character_id -eq $expected)
        $detail = "in=" + $c.Input + "; expected=" + $expected + "; actual=" + [string]$latest.active_character_id
        Write-Step ("Character Mapping - " + $c.Name) $ok $detail
        $results += $ok
    } catch {
        Write-Step ("Character Mapping - " + $c.Name) $false $_.Exception.Message
        $results += $false
    }
}

try {
    $final = Invoke-JsonGet -url $latestUrl
    $required = @("timestamp","active_character_id","risk_level","public_signal_direction","abstract_reason","schema_version","event_id","source")
    $missing = @()
    foreach ($k in $required) {
        if (-not ($final.PSObject.Properties.Name -contains $k)) { $missing += $k }
    }
    $okSchema = ($missing.Count -eq 0)
    $schemaDetail = "required keys present"
    if (-not $okSchema) {
        $schemaDetail = "missing: " + ($missing -join ", ")
    }
    Write-Step "Latest Schema Integrity" $okSchema $schemaDetail
    $results += $okSchema
} catch {
    Write-Step "Latest Schema Integrity" $false $_.Exception.Message
    $results += $false
}

$allOk = -not ($results -contains $false)
if ($allOk) {
    Write-Host "Overall: READY (E2E smoke)" -ForegroundColor Green
    exit 0
}

Write-Host "Overall: INCOMPLETE (E2E smoke)" -ForegroundColor Yellow
exit 1
