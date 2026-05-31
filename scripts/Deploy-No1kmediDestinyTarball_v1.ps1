<#
.SYNOPSIS
  Deploy projects/no1kmedi to VPS PM2 path via tarball (when VPS git pull lags local bare).

.DESCRIPTION
  PM2 no1kmedi-com exec cwd: /opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi

  Recommended order (local):
    1. Commit + push monorepo to internal (scripts/push-internal.ps1) so VPS can ff-only pull scripts/data/schemas.
    2. Run this script (tarball overwrites projects/no1kmedi; monorepo root is synced via git pull on VPS).

  Sets on VPS .env.local (never shipped in tarball): MKM_WORKSPACE_ROOT, MKM_PYTHON, KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Deploy-No1kmediDestinyTarball_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Deploy-No1kmediDestinyTarball_v1.ps1 -SkipMonorepoSync -RunApiSmoke
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SshIdentityFile = "",
    [string]$MonorepoRemote = "origin",
    [string]$MonorepoBranch = "main",
    [switch]$DryRun,
    [switch]$SkipLocalBuild,
    [switch]$SkipMonorepoSync,
    [switch]$SkipMonorepoPathsFromLocal,
    [switch]$RunApiSmoke
)

$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$vpsDestinyRepo = "/opt/mkm-destiny-ai-41e38ec6"
$vpsDest = "$vpsDestinyRepo/projects/no1kmedi"
$vpsParent = "$vpsDestinyRepo/projects"
$src = Join-Path $WorkspaceRoot "projects\no1kmedi"

if (-not (Test-Path $src)) { throw "missing $src" }

$sshArgs = @()
if ($SshIdentityFile) { $sshArgs = @("-i", $SshIdentityFile) }
else {
    $extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
    if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }
}

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$tarLocal = Join-Path $env:TEMP "no1kmedi-deploy-$stamp.tar.gz"
$tarRemote = "/tmp/no1kmedi-deploy-$stamp.tar.gz"

$monorepoRequiredPaths = @(
    "$vpsDestinyRepo/scripts/build_km_physician_cds_assist_envelope_v1.py",
    "$vpsDestinyRepo/scripts/build_patient_care_bundle_from_km_cds_chain_v1.py",
    "$vpsDestinyRepo/data/myeongni/myeongni_school_conflict_resolver_v1.json",
    "$vpsDestinyRepo/docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json",
    "$vpsDestinyRepo/docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json"
)

if (-not $SkipMonorepoSync) {
    $pullCmd = (@"
cd $vpsDestinyRepo
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch $MonorepoRemote $MonorepoBranch && git pull --ff-only $MonorepoRemote $MonorepoBranch || echo '[no1kmedi-tarball] WARN: git pull failed (will try local path sync)'
else
  echo '[no1kmedi-tarball] WARN: monorepo not a git checkout — skip pull'
fi
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

    Write-Host "[no1kmedi-tarball] VPS monorepo: git pull $MonorepoRemote/$MonorepoBranch (best-effort)" -ForegroundColor Cyan
    if (-not $DryRun) {
        & ssh @($sshArgs + @($remote, $pullCmd))
    }
}

if (-not $SkipMonorepoPathsFromLocal) {
    $localMono = $WorkspaceRoot
    $relFiles = @(
        "scripts/build_km_physician_cds_assist_envelope_v1.py",
        "scripts/build_patient_care_bundle_from_km_cds_chain_v1.py",
        "scripts/assemble_patient_care_bundle_with_myeongni_v1.py",
        "scripts/build_myeongni_full_report_v1.py",
        "scripts/run_saju_global_birth_v1.py",
        "scripts/saju_birth_resolver_v1.py",
        "scripts/apply_patient_care_bundle_slot_templates_v1.py",
        "scripts/validate_patient_care_bundle_against_policy_v1.py",
        "scripts/render_patient_care_bundle_markdown_v1.py",
        "docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json",
        "docs/final/schemas/mkm_bianzheng_tri_layer_v1.schema.json",
        "docs/final/schemas/patient_care_bundle_v1.schema.json",
        "docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json",
        "docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json",
        "docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json",
        "tests/fixtures/patient_care_bundle_soap_stub_v1.example.json"
    )
    Write-Host "[no1kmedi-tarball] scp monorepo CDS/bundle paths from local" -ForegroundColor Cyan
    if (-not $DryRun) {
        & ssh @($sshArgs + @($remote, "mkdir -p $vpsDestinyRepo/scripts $vpsDestinyRepo/docs/final/schemas $vpsDestinyRepo/docs/final/artifacts $vpsDestinyRepo/tests/fixtures $vpsDestinyRepo/data/myeongni"))
        foreach ($rel in $relFiles) {
            $localPath = Join-Path $localMono $rel
            if (-not (Test-Path $localPath)) { throw "missing local monorepo file: $localPath" }
            $remoteDir = "$vpsDestinyRepo/" + ($rel -replace "/[^/]+$", "" -replace "\\", "/")
            & scp @($sshArgs + @($localPath, "${remote}:${remoteDir}/"))
            if ($LASTEXITCODE -ne 0) { throw "scp failed: $rel" }
        }
        $myeongniLocal = Join-Path $localMono "data\myeongni"
        if (Test-Path $myeongniLocal) {
            & scp @($sshArgs + @("-r", $myeongniLocal, "${remote}:$vpsDestinyRepo/data/"))
            if ($LASTEXITCODE -ne 0) { throw "scp data/myeongni failed" }
        }
    }
}

if (-not $SkipMonorepoSync -or -not $SkipMonorepoPathsFromLocal) {
    $pathList = ($monorepoRequiredPaths | ForEach-Object { "'$_'" }) -join " "
    $gateCmd = (@"
set -e
for f in $pathList; do
  test -f "`$f" || { echo "missing: `$f"; exit 1; }
done
echo '[no1kmedi-tarball] monorepo path gate OK'
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"
    Write-Host "[no1kmedi-tarball] monorepo path gate" -ForegroundColor Cyan
    if (-not $DryRun) {
        & ssh @($sshArgs + @($remote, $gateCmd))
        if ($LASTEXITCODE -ne 0) { throw "monorepo path gate failed on VPS" }
    }
}

if (-not $SkipLocalBuild) {
    Write-Host "[no1kmedi-tarball] local npm run build" -ForegroundColor Cyan
    Push-Location $src
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw "local build failed exit $LASTEXITCODE" }
    } finally { Pop-Location }
}

Write-Host "[no1kmedi-tarball] archive (excludes node_modules/.next/.env.local)" -ForegroundColor Cyan
if (Test-Path $tarLocal) { Remove-Item $tarLocal -Force }
& tar -czf $tarLocal -C (Join-Path $WorkspaceRoot "projects") --exclude=node_modules --exclude=.next --exclude=.env.local no1kmedi
if ($LASTEXITCODE -ne 0) { throw "tar failed" }

if ($DryRun) {
    Write-Host "DRY-RUN: scp $tarLocal -> ${remote}:$tarRemote"
    Write-Host "DRY-RUN: ssh extract -> $vpsDest ; npm ci ; npm run build ; pm2 restart no1kmedi-com"
    exit 0
}

Write-Host "[no1kmedi-tarball] scp" -ForegroundColor Cyan
& scp @($sshArgs + @($tarLocal, "${remote}:${tarRemote}"))
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

$remoteCmd = (@"
mkdir -p $vpsParent
rm -rf ${vpsDest}.bak.${stamp} 2>/dev/null || true
test -d $vpsDest && mv $vpsDest ${vpsDest}.bak.${stamp} || true
mkdir -p $vpsDest
tar -xzf $tarRemote -C $vpsParent
cd $vpsDest && npm ci && npm run build
ENV_FILE="$vpsDest/.env.local"
touch "`$ENV_FILE"
grep -q '^MKM_WORKSPACE_ROOT=' "`$ENV_FILE" && sed -i 's|^MKM_WORKSPACE_ROOT=.*|MKM_WORKSPACE_ROOT=$vpsDestinyRepo|' "`$ENV_FILE" || echo "MKM_WORKSPACE_ROOT=$vpsDestinyRepo" >> "`$ENV_FILE"
grep -q '^KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN=' "`$ENV_FILE" || echo 'KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN=1' >> "`$ENV_FILE"
grep -q '^MKM_PYTHON=' "`$ENV_FILE" && sed -i 's|^MKM_PYTHON=.*|MKM_PYTHON=/usr/bin/python3|' "`$ENV_FILE" || echo 'MKM_PYTHON=/usr/bin/python3' >> "`$ENV_FILE"
pm2 restart no1kmedi-com --update-env || pm2 start npm --name no1kmedi-com --cwd $vpsDest -- start
pm2 save
rm -f $tarRemote
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

Write-Host "[no1kmedi-tarball] remote build + pm2" -ForegroundColor Cyan
& ssh @($sshArgs + @($remote, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "remote deploy failed" }

Start-Sleep -Seconds 6
$smokeUrls = @(
    "https://app.jema-ai.com/enterprise",
    "https://app.jema-ai.com/clinician"
)
foreach ($entUrl in $smokeUrls) {
    Write-Host "[no1kmedi-tarball] smoke GET $entUrl" -ForegroundColor Cyan
    $httpCode = (& curl.exe -s -o NUL -w "%{http_code}" -L --max-time 30 $entUrl)
    if (@("200", "301", "302") -notcontains "$httpCode") {
        throw "[no1kmedi-tarball] smoke failed: $entUrl (http $httpCode)"
    }
}

if ($RunApiSmoke) {
    Write-Host "[no1kmedi-tarball] smoke POST advanced-consult (validate envelope)" -ForegroundColor Cyan
    $consultJson = @'
{"schema":"patient_consult_input_v1","request_id":"deploy_smoke","actor_id":"deploy","lane_a_profile":{"birth_instant_utc":"1987-12-31T15:00:00Z","iana_tz":"Asia/Seoul","constitution_survey":{"digestion_pattern":"post-meal bloating"}},"lane_b_clinical":{"chief_complaint":"chronic fatigue","onset":"6mo","severity":"moderate","medication":"none","health_survey":{"sleep_quality":"delayed sleep onset"}}}
'@
    $consultBody = Join-Path $env:TEMP "no1kmedi-deploy-consult-body-$stamp.json"
    [System.IO.File]::WriteAllText($consultBody, $consultJson.Trim(), [System.Text.UTF8Encoding]::new($false))
    $consultOut = Join-Path $env:TEMP "no1kmedi-deploy-consult-$stamp.json"
    $consultCode = (& curl.exe -s -o $consultOut -w "%{http_code}" --max-time 60 -X POST "https://app.jema-ai.com/api/cdss/advanced-consult?validate_km_cds_envelope=1" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" --data-binary "@$consultBody")
    if ($consultCode -ne "200") { throw "advanced-consult smoke failed http $consultCode" }
    $consult = Get-Content $consultOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $consult.km_cds.validation.ok) {
        throw "km_cds.validation not ok: $($consult.km_cds.validation.error)"
    }
    Write-Host "[no1kmedi-tarball] smoke POST patient-care-bundle-from-cds" -ForegroundColor Cyan
    $bundleReq = @{
        schema = "patient_care_bundle_from_cds_request_v1"
        request_id = "deploy_smoke"
        birth_instant_utc = "1987-12-31T15:00:00Z"
        iana_tz = "Asia/Seoul"
        cds_envelope = $consult.km_cds.envelope
        soap = @{
            subjective = @{ text = "chronic fatigue (deploy smoke)" }
            objective = @{ text = "not recorded" }
            assessment = @{ text = "preliminary hypothesis" }
            plan = @{ text = "physician confirmation" }
        }
        options = @{
            apply_slot_templates = $true
            validate_policy = $true
            validate_bundle = $true
            render_patient_md = $true
        }
    } | ConvertTo-Json -Depth 25 -Compress
    $bundleFile = Join-Path $env:TEMP "no1kmedi-deploy-bundle-$stamp.json"
    [System.IO.File]::WriteAllText($bundleFile, $bundleReq, [System.Text.UTF8Encoding]::new($false))
    $bundleOut = Join-Path $env:TEMP "no1kmedi-deploy-bundle-resp-$stamp.json"
    $bundleCode = (& curl.exe -s -o $bundleOut -w "%{http_code}" --max-time 90 -X POST "https://app.jema-ai.com/api/cdss/patient-care-bundle-from-cds" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" -H "Referer: https://app.jema-ai.com/clinician" --data-binary "@$bundleFile")
    if ($bundleCode -ne "200") { throw "patient-care-bundle smoke failed http $bundleCode" }
    $bundle = Get-Content $bundleOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $bundle.success) { throw "patient-care-bundle success=false" }
    $mdLen = ($bundle.patient_facing_markdown | Out-String).Trim().Length
    if ($mdLen -lt 20) { throw "patient_facing_markdown too short ($mdLen)" }
    Write-Host "[no1kmedi-tarball] API smoke OK (md_len=$mdLen)" -ForegroundColor Green
}

Remove-Item $tarLocal -Force -ErrorAction SilentlyContinue
Write-Host "[no1kmedi-tarball] OK" -ForegroundColor Green
