<#
.SYNOPSIS
  Save YouTube ingest RTMP URL to User env YOUTUBE_RTMP_URL and refresh ambient_stream_rtmp_command.

.EXAMPLE
  pwsh -File scripts\Set-YoutubeRtmpUrlUserEnv_v1.ps1 -RtmpUrl "rtmp://a.rtmp.youtube.com/live2/xxxx-xxxx-xxxx-xxxx"
  pwsh -File scripts\Set-YoutubeRtmpUrlUserEnv_v1.ps1 -FromDotEnv
  pwsh -File scripts\Set-YoutubeRtmpUrlUserEnv_v1.ps1 -FromDotEnv -WhatIfOnly
#>
[CmdletBinding(DefaultParameterSetName = "Explicit")]
param(
    [Parameter(Mandatory = $true, ParameterSetName = "Explicit")]
    [string]$RtmpUrl,

    [Parameter(Mandatory = $true, ParameterSetName = "FromDotEnv")]
    [switch]$FromDotEnv,

    [Parameter(ParameterSetName = "FromDotEnv")]
    [string]$DotEnvPath,

    [switch]$WhatIfOnly,
    [switch]$SkipRegenerateCommand,
    [switch]$QuietMissing
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Read-DotEnvValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $s = $line.Trim()
        if (-not $s -or $s.StartsWith("#")) { continue }
        if ($s.StartsWith("export ")) { $s = $s.Substring(7).Trim() }
        $idx = $s.IndexOf("=")
        if ($idx -lt 1) { continue }
        $k = $s.Substring(0, $idx).Trim()
        if ($k -ne $Key) { continue }
        $v = $s.Substring($idx + 1).Trim()
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        return $v
    }
    return $null
}

if ($PSCmdlet.ParameterSetName -eq "FromDotEnv") {
    $envFile = if ($DotEnvPath) { $DotEnvPath } else { Join-Path $RepoRoot ".env" }
    $RtmpUrl = Read-DotEnvValue -Path $envFile -Key "YOUTUBE_RTMP_URL"
    if (-not $RtmpUrl -or -not $RtmpUrl.Trim()) {
        if ($QuietMissing) { exit 0 }
        Write-Error "YOUTUBE_RTMP_URL missing in $envFile (add one line; never commit real keys)."
    }
}

$u = $RtmpUrl.Trim()
if (-not $u.StartsWith("rtmp://", [StringComparison]::OrdinalIgnoreCase)) {
    throw "RtmpUrl must start with rtmp:// (YouTube ingest URL + stream key in one line)."
}
if ($u -match '[\r\n]') {
    throw "RtmpUrl must be a single line."
}

$redacted = if ($u.Length -gt 40) { $u.Substring(0, 28) + "..." } else { "rtmp://..." }
Write-Host "target: User env YOUTUBE_RTMP_URL"
Write-Host "value:  $redacted"

if ($WhatIfOnly) {
    Write-Host "whatif: no env write"
    exit 0
}

[Environment]::SetEnvironmentVariable("YOUTUBE_RTMP_URL", $u, "User")
$env:YOUTUBE_RTMP_URL = $u
Write-Host "OK: User env YOUTUBE_RTMP_URL set (new processes inherit; restart Cursor/terminal if needed)."

if (-not $SkipRegenerateCommand) {
    & py (Join-Path $RepoRoot "scripts\emit_ambient_stream_rtmp_command_v1.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "OK: reports\ambient_stream_rtmp_command_latest.txt refreshed (real RTMP URL embedded)."
}

exit 0
