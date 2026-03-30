param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-JsonUtf8 {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Data
    )
    $json = $Data | ConvertTo-Json -Depth 16
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$today = (Get-Date).ToUniversalTime().ToString("yyyyMMdd")
$tsIso = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$btrackRoot = Join-Path $root "data\logos\btrack_pilot"
$dirs = @(
    $btrackRoot,
    (Join-Path $btrackRoot "incoming"),
    (Join-Path $btrackRoot "normalized"),
    (Join-Path $btrackRoot "bench"),
    (Join-Path $btrackRoot "snapshots"),
    (Join-Path $btrackRoot "gates"),
    (Join-Path $btrackRoot "logs"),
    (Join-Path $root "reports\constitution\btrack_pilot")
)

foreach ($d in $dirs) { Ensure-Directory -Path $d }

$manifestPath = Join-Path $root "data\logos\manuscripts\LOGOS_DSS_MANIFEST.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host "[btrack-init] LOGOS_DSS_MANIFEST.json missing. Building..."
    & py (Join-Path $root "scripts\build_logos_dss_manifest.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build LOGOS_DSS_MANIFEST.json (exit=$LASTEXITCODE)."
    }
}

$pilotMetaPath = Join-Path $btrackRoot "pilot_meta.json"
$pilotMeta = @{
    schema = "btrack_pilot_meta_v1"
    generated_at_utc = $tsIso
    track_policy = @{
        a_track = "frozen_core_readonly"
        b_track = "isolated_satellite_corpus"
        direct_injection_to_production = $false
    }
    states = @(
        "verified",
        "partial_anchor_verified",
        "excluded",
        "candidate_for_promotion"
    )
    source_paths = @{
        dss_jsonl = "data/logos/manuscripts/dss_parsed.jsonl"
        apocrypha_jsonl = "data/logos/manuscripts/apocrypha_std.jsonl"
        dss_manifest = "data/logos/manuscripts/LOGOS_DSS_MANIFEST.json"
    }
    benchmark_files = @{
        a_track_results = "data/logos/btrack_pilot/bench/a_track_eval.jsonl"
        b_track_results = "data/logos/btrack_pilot/bench/b_track_eval.jsonl"
        quality_report = "reports/constitution/btrack_pilot/btrack_quality_latest.json"
    }
    required_metrics = @(
        "reproducibility",
        "resolution",
        "contamination"
    )
}

if ((Test-Path -LiteralPath $pilotMetaPath) -and (-not $Force)) {
    Write-Host "[btrack-init] pilot_meta.json already exists. Use -Force to overwrite."
} else {
    Write-JsonUtf8 -Path $pilotMetaPath -Data $pilotMeta
    Write-Host "[btrack-init] wrote $pilotMetaPath"
}

$gateTemplatePath = Join-Path $btrackRoot "gates\promotion_gate_template.json"
$gateTemplate = @{
    schema = "btrack_promotion_gate_v1"
    generated_at_utc = $tsIso
    thresholds = @{
        reproducibility_match_rate_min = 0.80
        resolution_confidence_delta_min = 0.00
        contamination_snr_delta_min = 0.00
    }
    decision = "pending"
    notes = "Set thresholds by domain owner before production promotion."
}
if ((Test-Path -LiteralPath $gateTemplatePath) -and (-not $Force)) {
    Write-Host "[btrack-init] promotion gate template already exists. Use -Force to overwrite."
} else {
    Write-JsonUtf8 -Path $gateTemplatePath -Data $gateTemplate
    Write-Host "[btrack-init] wrote $gateTemplatePath"
}

$readmePath = Join-Path $btrackRoot "logs\pilot_init_$today.log"
$logLine = "{0} init_complete root={1} force={2}" -f $tsIso, $btrackRoot, [bool]$Force
[System.IO.File]::AppendAllText($readmePath, $logLine + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
Write-Host "[btrack-init] logged $readmePath"
Write-Host "[btrack-init] done"
