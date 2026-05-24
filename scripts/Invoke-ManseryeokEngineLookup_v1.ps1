# Engine-only manseryeok lookup (B-track). No LLM.
param(
    [string]$UtcInstant = "",
    [string]$IanaTz = "Asia/Seoul",
    [string]$RequestJson = "",
    [string]$OutJson = "reports/manseryeok_engine_lookup_latest.json",
    [switch]$Compact,
    [switch]$StdoutOnly
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $pyArgs = @("scripts/manseryeok_engine_lookup_v1.py")
    if ($RequestJson) {
        $pyArgs += @("--request-json", $RequestJson)
    } elseif ($UtcInstant) {
        $pyArgs += @("--utc-instant", $UtcInstant, "--iana-tz", $IanaTz)
    } else {
        Write-Error "Provide -UtcInstant or -RequestJson"
    }
    if (-not $StdoutOnly) {
        $pyArgs += @("--out", $OutJson)
    }
    if ($Compact) { $pyArgs += "--compact" }
    & py @pyArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
