param(
    [string[]]$Sequence = @("conservative", "balanced", "aggressive"),
    [string]$StatePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\gate_profile_rotation_state.json",
    [switch]$PersistUserEnv,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Resolve-NextProfile {
    param(
        [string[]]$Seq,
        [string]$StateFile
    )

    if ($Seq.Count -lt 1) {
        throw "Sequence must contain at least one profile."
    }

    $normalized = @($Seq | ForEach-Object { ([string]$_).Trim().ToLowerInvariant() })
    $allowed = @("conservative", "balanced", "aggressive")
    foreach ($p in $normalized) {
        if ($allowed -notcontains $p) {
            throw "Invalid profile in sequence: $p"
        }
    }

    $current = $null
    if (Test-Path -LiteralPath $StateFile) {
        try {
            $doc = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
            $candidate = [string]$doc.current_profile
            if (-not [string]::IsNullOrWhiteSpace($candidate)) {
                $current = $candidate.Trim().ToLowerInvariant()
            }
        } catch {
            # ignore broken state and restart rotation
            $current = $null
        }
    }

    $idx = -1
    if (-not [string]::IsNullOrWhiteSpace($current)) {
        $idx = [Array]::IndexOf($normalized, $current)
    }
    if ($idx -lt 0) {
        return $normalized[0]
    }
    return $normalized[($idx + 1) % $normalized.Count]
}

$applyScript = Join-Path $PSScriptRoot "apply_dual_regime_gate_profile_and_restart.ps1"
if (-not (Test-Path -LiteralPath $applyScript)) {
    throw "Missing apply script: $applyScript"
}

$stateDir = Split-Path -Parent $StatePath
if (-not (Test-Path -LiteralPath $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

$next = Resolve-NextProfile -Seq $Sequence -StateFile $StatePath
Write-Host ("[gate-rotation] next profile: {0}" -f $next)

if ($WhatIf) {
    if ($PersistUserEnv) {
        Write-Host ("[whatif] Would run: {0} -Profile {1} -PersistUserEnv" -f $applyScript, $next)
    } else {
        Write-Host ("[whatif] Would run: {0} -Profile {1}" -f $applyScript, $next)
    }
} else {
    if ($PersistUserEnv) {
        & $applyScript -Profile $next -PersistUserEnv
    } else {
        & $applyScript -Profile $next
    }
}

$state = [ordered]@{
    schema = "gate_profile_rotation_state_v1"
    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    current_profile = $next
    sequence = @($Sequence | ForEach-Object { ([string]$_).Trim().ToLowerInvariant() })
}
$state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8

Write-Host ("[gate-rotation] state written: {0}" -f $StatePath)

