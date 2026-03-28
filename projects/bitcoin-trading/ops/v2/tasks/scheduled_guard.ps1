# Scheduled guard: throttle repeated ops runs by task key + minimum interval.
# Dot-source this file, then call Invoke-ScheduledGuardedRun.

function Invoke-ScheduledGuardedRun {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskKey,

        [Parameter(Mandatory = $true)]
        [string]$StateDir,

        [Parameter(Mandatory = $true)]
        [int]$MinIntervalSeconds,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Action,

        [bool]$DryRun = $false,

        [switch]$Force
    )

    $safeKey = ($TaskKey -replace '[^\w\-\.]', '_')
    if ([string]::IsNullOrWhiteSpace($safeKey)) {
        $safeKey = "task"
    }

    if (-not (Test-Path -LiteralPath $StateDir)) {
        New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
    }

    $statePath = Join-Path $StateDir "$safeKey.json"

    if ($DryRun) {
        return @{
            ran    = $false
            reason = "dry_run"
        }
    }

    $now = [datetime]::UtcNow
    $elapsedOk = $true
    $skipReason = $null

    if (Test-Path -LiteralPath $statePath) {
        try {
            $raw = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8
            $obj = $raw | ConvertFrom-Json
            if ($null -ne $obj -and $obj.PSObject.Properties.Name -contains 'lastRunUtc') {
                $last = [datetime]::Parse($obj.lastRunUtc, $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
                $elapsed = ($now - $last.ToUniversalTime()).TotalSeconds
                if ($elapsed -lt $MinIntervalSeconds) {
                    $elapsedOk = $false
                    $skipReason = "min_interval_not_elapsed ($([math]::Floor($elapsed))s < ${MinIntervalSeconds}s)"
                }
            }
        }
        catch {
            $elapsedOk = $true
        }
    }

    if ($Force) {
        $elapsedOk = $true
    }

    if (-not $elapsedOk) {
        return @{
            ran    = $false
            reason = $skipReason
        }
    }

    & $Action

    $payload = [ordered]@{
        lastRunUtc = $now.ToString("o")
        taskKey    = $TaskKey
    }
    ($payload | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $statePath -Encoding UTF8 -Force

    return @{
        ran    = $true
        reason = $null
    }
}
