[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet(2, 3, 4, 'all')]
    $Post = 'all',

    [Parameter(Mandatory = $false)]
    [switch]$SkipBrowser,

    [Parameter(Mandatory = $false)]
    [switch]$SkipEvidenceCapture,

    [Parameter(Mandatory = $false)]
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$PasteDir = Join-Path $Root 'reports/human_paste'
$ComposeUrl = 'https://x.com/compose/post'
$EvidencePng = Join-Path $PasteDir 'universal_root_smoke_terminal_evidence.png'
$CaptureScript = Join-Path $Root 'scripts/capture_universal_root_smoke_evidence_v1.py'

function Get-PostPath([int]$Number) {
    Join-Path $PasteDir ("universal_root_x_post_{0}.txt" -f $Number)
}

function Invoke-UniversalRootXPostStep([int]$Number) {
    $path = Get-PostPath -Number $Number
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing paste file: $path"
    }
    $text = Get-Content -LiteralPath $path -Raw -Encoding UTF8
    Set-Clipboard -Value $text.TrimEnd()
    Write-Host "[UR-GTM] Post $Number copied to clipboard ($([math]::Min($text.Length, 280)) chars shown max in UI)." -ForegroundColor Green
    Write-Host $text.TrimEnd()
    Write-Host ''

    if ($Number -eq 2) {
        if (-not (Test-Path -LiteralPath $EvidencePng)) {
            Write-Warning "Smoke evidence PNG missing. Run: py scripts/capture_universal_root_smoke_evidence_v1.py"
        }
        else {
            Write-Host "[UR-GTM] Attach screenshot: $EvidencePng" -ForegroundColor Cyan
            if (-not $SkipBrowser) {
                Start-Process -FilePath $EvidencePng
            }
        }
    }

    if (-not $SkipBrowser) {
        Start-Process $ComposeUrl
        Write-Host '[UR-GTM] Compose opened - paste (Ctrl+V), attach image for post 2, click Post manually.' -ForegroundColor Yellow
    }
}

if (-not $SkipEvidenceCapture -and ($Post -eq 2 -or $Post -eq 'all')) {
    Write-Host '[UR-GTM] Capturing smoke evidence for post 2...' -ForegroundColor Cyan
    & py $CaptureScript
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Smoke evidence capture failed; continue with text-only paste.'
    }
}

$numbers = if ($Post -eq 'all') { @(2, 3, 4) } else { @([int]$Post) }
foreach ($n in $numbers) {
    if ($Post -eq 'all' -and $numbers.Count -gt 1 -and -not $NonInteractive) {
        Read-Host "Press Enter when ready for X post $n (clipboard will update)"
    }
    Invoke-UniversalRootXPostStep -Number $n
}

Write-Host '[UR-GTM] After all posts: tell agent "X 2-4 posted" (+ URLs if any).' -ForegroundColor Cyan
