[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet(2, 3, 4, 'all')]
    $Post = 'all',

    [Parameter(Mandatory = $false)]
    [switch]$DryRun,

    [Parameter(Mandatory = $false)]
    [switch]$VerifyAuth,

    [Parameter(Mandatory = $false)]
    [switch]$AcknowledgeSend,

    [Parameter(Mandatory = $false)]
    [switch]$CorrectionReply,

    [Parameter(Mandatory = $false)]
    [string]$ReplyTo = '2068734802661175789',

    [Parameter(Mandatory = $false)]
    [switch]$SkipEvidenceCapture
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$PostScript = Join-Path $Root 'scripts/post_x_api_v1.py'
$CaptureScript = Join-Path $Root 'scripts/capture_universal_root_smoke_evidence_v1.py'
$StoreScript = Join-Path $Root 'scripts/Invoke-EncryptedSecretStore.ps1'

function Get-DpapiPlain([string]$Key) {
    $val = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StoreScript -Action get -Key $Key -AsPlainText
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($val)) {
        throw "DPAPI get failed for $Key (exit $LASTEXITCODE)"
    }
    return $val.Trim()
}

function Set-XApiEnvFromDpapi {
    $names = @(
        'MKM_X_API_KEY',
        'MKM_X_API_SECRET',
        'MKM_X_ACCESS_TOKEN',
        'MKM_X_ACCESS_TOKEN_SECRET'
    )
    foreach ($name in $names) {
        Set-Item -Path "Env:$name" -Value (Get-DpapiPlain -Key $name)
    }
}

if (-not $DryRun) {
    Set-XApiEnvFromDpapi
}
elseif ($VerifyAuth) {
    Set-XApiEnvFromDpapi
}

if (-not $SkipEvidenceCapture -and ($Post -eq 2 -or $Post -eq 'all')) {
    Write-Host '[UR-GTM] Capturing smoke evidence for post 2...' -ForegroundColor Cyan
    & py $CaptureScript
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Smoke evidence capture failed; post 2 may fail without PNG.'
    }
}

$postsArg = if ($Post -eq 'all') { '2,3,4' } else { [string]$Post }
$pyArgs = @($PostScript)
if ($CorrectionReply) {
    $pyArgs += '--correction-reply', '--reply-to', $ReplyTo
} else {
    $pyArgs += '--posts', $postsArg
}
if ($DryRun) { $pyArgs += '--dry-run' }
if ($VerifyAuth) { $pyArgs += '--verify-auth' }
if ($AcknowledgeSend) { $pyArgs += '--acknowledge-send' }

& py @pyArgs
$code = $LASTEXITCODE
if ($code -eq 0 -and $AcknowledgeSend -and -not $DryRun) {
    if ($CorrectionReply) {
        Write-Host '[UR-GTM] Sync GTM: py scripts/sync_universal_root_community_gtm_v1.py --x-correction-replied' -ForegroundColor Cyan
        & py (Join-Path $Root 'scripts/sync_universal_root_community_gtm_v1.py') --x-correction-replied
    } else {
        Write-Host '[UR-GTM] Sync GTM: py scripts/sync_universal_root_community_gtm_v1.py --x-posts-2-4-posted' -ForegroundColor Cyan
        & py (Join-Path $Root 'scripts/sync_universal_root_community_gtm_v1.py') --x-posts-2-4-posted
    }
}
exit $code
