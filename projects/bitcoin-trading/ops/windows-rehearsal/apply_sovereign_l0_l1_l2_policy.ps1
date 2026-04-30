param(
    [string]$PolicyJsonPath = "C:\workspace\projects\bitcoin-trading\config\sovereign_l0_l1_l2_policy.template.json",
    [string]$EnvPath = "C:\workspace\.env"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $PolicyJsonPath)) {
    throw "Policy JSON not found: $PolicyJsonPath"
}

$policy = Get-Content -LiteralPath $PolicyJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $policy -or [string]::IsNullOrWhiteSpace([string]$policy.schema)) {
    throw "Invalid policy JSON: schema missing"
}

$kv = [ordered]@{
    "MKM_L2_RECYCLE_WINDOW_HOURS"      = [string]$policy.l2.recycle_window_hours
    "MKM_L2_RECYCLE_MIN_COUNT"         = [string]$policy.l2.recycle_min_count
    "MKM_L2_SAME_CODE_RATIO_MIN"       = [string]$policy.l2.same_failure_code_ratio_min
    "MKM_L2_COOLDOWN_MINUTES"          = [string]$policy.l2.post_recovery_cooldown_minutes
    "MKM_L1_ADAPT_MAX_PCT"             = [string]$policy.l1.max_adapt_pct
    "MKM_SINGULAR_CORE_THRESHOLD"      = [string]$policy.defaults.MKM_SINGULAR_CORE_THRESHOLD
    "MKM_MIN_CONFIDENCE"               = [string]$policy.defaults.MKM_MIN_CONFIDENCE
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    New-Item -ItemType File -Path $EnvPath -Force | Out-Null
}

$lines = Get-Content -LiteralPath $EnvPath -Encoding UTF8
$updated = New-Object System.Collections.Generic.List[string]
$seen = @{}

foreach ($line in $lines) {
    $current = $line
    $replaced = $false
    foreach ($key in $kv.Keys) {
        if ($current -match ("^\s*" + [regex]::Escape($key) + "\s*=")) {
            if (-not $seen.ContainsKey($key)) {
                $updated.Add("$key=$($kv[$key])")
                $seen[$key] = $true
            }
            $replaced = $true
            break
        }
    }
    if (-not $replaced) {
        $updated.Add($current)
    }
}

foreach ($key in $kv.Keys) {
    if (-not $seen.ContainsKey($key)) {
        $updated.Add("$key=$($kv[$key])")
    }
}

Set-Content -LiteralPath $EnvPath -Value $updated -Encoding UTF8

Write-Host "Applied policy to .env:"
foreach ($key in $kv.Keys) {
    Write-Host ("- {0}={1}" -f $key, $kv[$key])
}
