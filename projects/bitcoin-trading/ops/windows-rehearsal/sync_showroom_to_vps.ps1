# Push local showroom static assets to Hostinger VPS web root via scp (OpenSSH). Cloudflare only fronts DNS/proxy.
# Topology SSOT: docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md — NOT hPanel public_html.
#
# Prereq: Windows OpenSSH Client (scp/ssh on PATH).
#
# By default, runs sync_required_env_to_user.ps1 first so MKM_VPS_* from C:\workspace\.env
# are written to Windows User scope (same hub as OPS bootstrap). Use -SkipDotenvUserSync to disable.
#
# Required env (Process or User):
#   MKM_VPS_HOST, MKM_VPS_USER
# Optional env:
#   JEMAAI_VPS_SHOWROOM_ROOT — remote directory (default /var/www/jemaai)
#   MKM_VPS_SCP_EXTRA_ARGS   — extra scp args, e.g. -i C:\Users\me\.ssh\id_ed25519
#   JEMAAI_VPS_RELOAD_NGINX  — set to 1 to run "sudo nginx -t && sudo systemctl reload nginx" after scp
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File sync_showroom_to_vps.ps1
#   powershell ... -RefreshStaging   # chain (freshness -> build -> validate) -> deploy_showroom_static -> scp
#   powershell ... -DryRun
#   powershell ... -SkipDotenvUserSync

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RefreshStaging,
    [switch]$DryRun,
    [switch]$SkipDotenvUserSync,
    [switch]$AllowPasswordPrompt,
    [switch]$ApplyRecommendedNginx,
    [switch]$NginxSnippetOnly
)

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$syncDotenv = Join-Path $here "sync_required_env_to_user.ps1"
$dotenvPath = Join-Path $WorkspaceRoot ".env"
if (-not $SkipDotenvUserSync -and (Test-Path -LiteralPath $syncDotenv) -and (Test-Path -LiteralPath $dotenvPath)) {
    Write-Host "[showroom-vps-sync] Applying .env -> User env (sync_required_env_to_user.ps1)..." -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $syncDotenv
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] sync_required_env_to_user.ps1 failed: $LASTEXITCODE"
    }
}

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

function Assert-Command([string]$name) {
    $cmd = Get-Command -Name $name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "[showroom-vps-sync] missing '$name' on PATH (install OpenSSH Client)."
    }
}

Assert-Command -name "scp"
Assert-Command -name "ssh"

$staging = Join-Path $here ".showroom_staging"
$html = Join-Path $staging "public_showroom_poll.html"
$htmlMinimal = Join-Path $staging "public_showroom_board_minimal.html"
$htmlTopologyRadar = Join-Path $staging "public_showroom_topology_radar_v1.html"
$json = Join-Path $staging "showroom_public_bundle_v1.json"
$jsonTopology = Join-Path $staging "showroom_topology_radar_snapshot_v1_latest.json"
$jsonMacroHorizon = Join-Path $staging "showroom_macro_horizon_2030_slice_v1_latest.json"
$htmlTrust = Join-Path $staging "public_showroom_trust_visualization_v0.html"
$jsonTrust = Join-Path $staging "showroom_trust_visualization_slice_v0.json"
$htmlLogos = Join-Path $staging "public_showroom_logos_research_v1.html"
$jsonLogos = Join-Path $staging "showroom_logos_research_slice_v0.json"
$htmlMeaningGraph = Join-Path $staging "public_showroom_meaning_topology_graph_v1.html"
$jsonMeaningGraph = Join-Path $staging "showroom_meaning_topology_graph_slice_v1.json"
$htmlMeaningQaV2 = Join-Path $staging "public_showroom_meaning_topology_qa_v2.html"
$jsonMeaningQaPresets = Join-Path $staging "showroom_meaning_topology_qa_presets_v1.json"
$htmlLogosOracleV3 = Join-Path $staging "public_showroom_logos_oracle_v3.html"
$htmlLogosOracleV4 = Join-Path $staging "public_showroom_logos_oracle_v4.html"
$htmlLogosOracleV5 = Join-Path $staging "public_showroom_logos_oracle_v5.html"
$htmlLogosOracleV6 = Join-Path $staging "public_showroom_logos_oracle_v6.html"
$jsonLogosChronologyOverlay = Join-Path $staging "showroom_logos_chronology_overlay_v1.json"
$htmlSaju = Join-Path $staging "public_showroom_probabilistic_saju_v1.html"
$jsonSaju = Join-Path $staging "showroom_saju_hour_bundle_demo_v1.json"
$htmlWireInterAgentV3 = Join-Path $staging "public_showroom_mkm_inter_agent_wire_v3.html"
$htmlSavingNews = Join-Path $staging "public_showroom_saving_the_news_matrix_v1.html"
$jsonSavingNewsPanel = Join-Path $staging "saving_the_news_matrix_panel_slice_v1_latest.json"
$jsonSavingNewsTopology = Join-Path $staging "saving_the_news_showroom_topology_slice_v1_latest.json"
$htmlLensAudio = Join-Path $staging "public_showroom_lens_audio_thin_slice_v1.html"
$htmlLensMedia = Join-Path $staging "public_showroom_lens_media_thin_slice_v1.html"
$jsonLensAudioSlice = Join-Path $staging "showroom_lens_audio_thin_slice_v1.json"
$jsonLensMediaSlice = Join-Path $staging "showroom_lens_media_thin_slice_v1.json"
$jsonLensAudioLut = Join-Path $staging "jemaai_lens_audio_playback_lut_v1_latest.json"
$jsonLensVideoLut = Join-Path $staging "jemaai_lens_video_playback_lut_v1_latest.json"
$audioLensBtrackDir = Join-Path $staging "audio\lens_btrack\v1"
$videoLensBtrackDir = Join-Path $staging "video\lens_btrack\v1"

if ($RefreshStaging) {
    Write-Host "[showroom-vps-sync] RefreshStaging: track_c chain -> deploy_showroom_static" -ForegroundColor Cyan
    $chain = Join-Path $WorkspaceRoot "scripts\build_showroom_track_c_bundle_chain_v1.ps1"
    $deploy = Join-Path $here "deploy_showroom_static.ps1"
    $bundleOut = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"

    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN would run: $chain -WorkspaceRoot $WorkspaceRoot ; $deploy"
    } else {
        if (-not (Test-Path -LiteralPath $chain)) {
            throw "Missing chain script: $chain"
        }
        $psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
        & $psExe -NoProfile -ExecutionPolicy Bypass -File $chain -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) { throw "build_showroom_track_c_bundle_chain_v1.ps1 failed: $LASTEXITCODE" }
        powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) { throw "deploy_showroom_static.ps1 failed: $LASTEXITCODE" }
    }
}

if (-not $NginxSnippetOnly) {
    if (-not (Test-Path -LiteralPath $html) -or -not (Test-Path -LiteralPath $htmlMinimal) -or -not (Test-Path -LiteralPath $json)) {
        throw "[showroom-vps-sync] staging files missing under $staging — run deploy_showroom_static.ps1 or use -RefreshStaging."
    }
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if ([string]::IsNullOrWhiteSpace($hostName) -or [string]::IsNullOrWhiteSpace($user)) {
    throw "[showroom-vps-sync] set MKM_VPS_HOST and MKM_VPS_USER (Process or User env)."
}

$remoteRoot = Get-EnvAny "JEMAAI_VPS_SHOWROOM_ROOT"
if ([string]::IsNullOrWhiteSpace($remoteRoot)) {
    $remoteRoot = "/var/www/jemaai"
}
$remoteRoot = $remoteRoot.TrimEnd("/")

$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$extraArgs = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $extraArgs = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

# Do not name the parameter $args — it collides with PowerShell's automatic $args and breaks -args binding.
function Test-HasIdentityArgs([string[]]$ScpLeadingArgs) {
    for ($i = 0; $i -lt $ScpLeadingArgs.Count; $i++) {
        $arg = $ScpLeadingArgs[$i]
        if ($arg -eq "-i") { return $true }
        if ($arg -like "-i*") { return $true }
        if ($arg -eq "-o" -and ($i + 1) -lt $ScpLeadingArgs.Count) {
            $next = $ScpLeadingArgs[$i + 1]
            if ($next -like "IdentityFile=*") { return $true }
        }
        if ($arg -like "IdentityFile=*") { return $true }
    }
    return $false
}

Write-Host "[showroom-vps-sync] remote_root=$remoteRoot host=$hostName user=$user" -ForegroundColor Cyan

# Single scp session (one password prompt when using password auth; static files -> same remote dir).
function Invoke-ScpShowroomPair {
    $remoteDir = "${user}@${hostName}:${remoteRoot}/"
    $argv = @()
    foreach ($a in $extraArgs) { $argv += $a }
    $argv += $html
    $argv += $htmlMinimal
    if (Test-Path -LiteralPath $htmlTopologyRadar) {
        $argv += $htmlTopologyRadar
    } else {
        Write-Host "[showroom-vps-sync] topology radar HTML not in staging (optional): $htmlTopologyRadar" -ForegroundColor DarkGray
    }
    $argv += $json
    if (Test-Path -LiteralPath $jsonTopology) {
        $argv += $jsonTopology
    } else {
        Write-Host "[showroom-vps-sync] topology snapshot not in staging (optional): $jsonTopology" -ForegroundColor DarkGray
    }
    if (Test-Path -LiteralPath $jsonMacroHorizon) {
        $argv += $jsonMacroHorizon
    } else {
        Write-Host "[showroom-vps-sync] macro horizon slice not in staging (optional): $jsonMacroHorizon" -ForegroundColor DarkGray
    }
    foreach ($pair in @(
            @{ Path = $htmlTrust; Label = "trust viz HTML" },
            @{ Path = $jsonTrust; Label = "trust viz JSON" },
            @{ Path = $htmlLogos; Label = "logos research HTML" },
            @{ Path = $jsonLogos; Label = "logos research JSON" },
            @{ Path = $htmlMeaningGraph; Label = "meaning topology graph HTML" },
            @{ Path = $jsonMeaningGraph; Label = "meaning topology graph JSON" },
            @{ Path = $htmlMeaningQaV2; Label = "meaning topology Q&A v2 HTML" },
            @{ Path = $jsonMeaningQaPresets; Label = "meaning topology Q&A presets JSON" },
            @{ Path = $htmlLogosOracleV3; Label = "logos oracle v3 HTML" },
            @{ Path = $htmlLogosOracleV4; Label = "logos oracle v4 visual path HTML" },
            @{ Path = $htmlLogosOracleV5; Label = "logos oracle v5 enterprise HTML" },
            @{ Path = $htmlLogosOracleV6; Label = "logos oracle v6 commercial HTML" },
            @{ Path = $jsonLogosChronologyOverlay; Label = "logos chronology overlay JSON" },
            @{ Path = $htmlSaju; Label = "probabilistic saju HTML" },
            @{ Path = $jsonSaju; Label = "saju hour bundle JSON" },
            @{ Path = $htmlWireInterAgentV3; Label = "MKM inter-agent wire v3 HTML" },
            @{ Path = $htmlSavingNews; Label = "Saving the News matrix HTML" },
            @{ Path = $jsonSavingNewsPanel; Label = "Saving the News panel slice JSON" },
            @{ Path = $jsonSavingNewsTopology; Label = "Saving the News topology slice JSON" },
            @{ Path = $htmlLensAudio; Label = "lens audio thin slice HTML" },
            @{ Path = $htmlLensMedia; Label = "lens media thin slice HTML" },
            @{ Path = $jsonLensAudioSlice; Label = "lens audio thin slice JSON" },
            @{ Path = $jsonLensMediaSlice; Label = "lens media thin slice JSON" },
            @{ Path = $jsonLensAudioLut; Label = "lens audio playback LUT JSON" },
            @{ Path = $jsonLensVideoLut; Label = "lens video playback LUT JSON" }
        )) {
        if (Test-Path -LiteralPath $pair.Path) {
            $argv += $pair.Path
        } else {
            Write-Host "[showroom-vps-sync] $($pair.Label) not in staging (optional): $($pair.Path)" -ForegroundColor DarkGray
        }
    }
    $argv += $remoteDir
    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN scp $($argv -join ' ')"
        return
    }
    $hasIdentity = Test-HasIdentityArgs -ScpLeadingArgs $extraArgs
    if (-not $AllowPasswordPrompt -and -not $hasIdentity) {
        throw "[showroom-vps-sync] blocked: non-interactive mode requires key auth. Set MKM_VPS_SCP_EXTRA_ARGS (e.g. '-i C:\Users\<user>\.ssh\id_ed25519') or re-run with -AllowPasswordPrompt."
    }
    & scp @argv
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] scp failed ($LASTEXITCODE)"
    }
}

function Invoke-ScpLensAudioAssets {
    if (-not (Test-Path -LiteralPath $audioLensBtrackDir)) {
        Write-Host "[showroom-vps-sync] lens audio WAV dir not in staging (optional): $audioLensBtrackDir" -ForegroundColor DarkGray
        return
    }
    $wavCount = @(Get-ChildItem -LiteralPath $audioLensBtrackDir -Filter "*.wav" -File -ErrorAction SilentlyContinue).Count
    if ($wavCount -le 0) {
        Write-Host "[showroom-vps-sync] lens audio staging dir empty (optional): $audioLensBtrackDir" -ForegroundColor DarkGray
        return
    }
    $remoteAudioDir = "${user}@${hostName}:${remoteRoot}/audio/lens_btrack/v1/"
    $argv = @()
    foreach ($a in $extraArgs) { $argv += $a }
    $argv += "-r"
    $argv += (Join-Path $audioLensBtrackDir "*")
    $argv += $remoteAudioDir
    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN scp lens audio $($argv -join ' ')"
        return
    }
    $hasIdentity = Test-HasIdentityArgs -ScpLeadingArgs $extraArgs
    if (-not $AllowPasswordPrompt -and -not $hasIdentity) {
        throw "[showroom-vps-sync] blocked: non-interactive mode requires key auth for lens audio scp."
    }
    $sshTarget = "${user}@${hostName}"
    $mkdirCmd = "mkdir -p ${remoteRoot}/audio/lens_btrack/v1"
    Write-Host "[showroom-vps-sync] ssh mkdir -p ${remoteRoot}/audio/lens_btrack/v1" -ForegroundColor Cyan
    & ssh @($extraArgs + @($sshTarget, $mkdirCmd))
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] ssh mkdir lens audio failed ($LASTEXITCODE)"
    }
    Write-Host "[showroom-vps-sync] scp lens audio WAV ($wavCount) -> ${remoteRoot}/audio/lens_btrack/v1/" -ForegroundColor Cyan
    & scp @argv
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] scp lens audio failed ($LASTEXITCODE)"
    }
}

function Invoke-ScpLensVideoAssets {
    if (-not (Test-Path -LiteralPath $videoLensBtrackDir)) {
        Write-Host "[showroom-vps-sync] lens video WEBM dir not in staging (optional): $videoLensBtrackDir" -ForegroundColor DarkGray
        return
    }
    $webmCount = @(Get-ChildItem -LiteralPath $videoLensBtrackDir -Filter "*.webm" -File -ErrorAction SilentlyContinue).Count
    if ($webmCount -le 0) {
        Write-Host "[showroom-vps-sync] lens video staging dir empty (optional): $videoLensBtrackDir" -ForegroundColor DarkGray
        return
    }
    $remoteVideoDir = "${user}@${hostName}:${remoteRoot}/video/lens_btrack/v1/"
    $argv = @()
    foreach ($a in $extraArgs) { $argv += $a }
    $argv += "-r"
    $argv += (Join-Path $videoLensBtrackDir "*")
    $argv += $remoteVideoDir
    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN scp lens video $($argv -join ' ')"
        return
    }
    $hasIdentity = Test-HasIdentityArgs -ScpLeadingArgs $extraArgs
    if (-not $AllowPasswordPrompt -and -not $hasIdentity) {
        throw "[showroom-vps-sync] blocked: non-interactive mode requires key auth for lens video scp."
    }
    $sshTarget = "${user}@${hostName}"
    $mkdirCmd = "mkdir -p ${remoteRoot}/video/lens_btrack/v1"
    Write-Host "[showroom-vps-sync] ssh mkdir -p ${remoteRoot}/video/lens_btrack/v1" -ForegroundColor Cyan
    & ssh @($extraArgs + @($sshTarget, $mkdirCmd))
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] ssh mkdir lens video failed ($LASTEXITCODE)"
    }
    Write-Host "[showroom-vps-sync] scp lens video WEBM ($webmCount) -> ${remoteRoot}/video/lens_btrack/v1/" -ForegroundColor Cyan
    & scp @argv
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] scp lens video failed ($LASTEXITCODE)"
    }
}

if (-not $NginxSnippetOnly) {
    Invoke-ScpShowroomPair
    Invoke-ScpLensAudioAssets
    Invoke-ScpLensVideoAssets
}

if ($ApplyRecommendedNginx -or $NginxSnippetOnly) {
    $snippetLocal = Join-Path $here "jemaai-cloud-mvp\nginx_snippets\jemaai_showroom_ui.conf"
    if (-not (Test-Path -LiteralPath $snippetLocal)) {
        throw "[showroom-vps-sync] missing nginx snippet: $snippetLocal"
    }
        $remoteSnippet = "/etc/nginx/snippets/jemaai_showroom_ui.conf"
        $audioSnippetLocal = Join-Path $here "jemaai-cloud-mvp\nginx_snippets\jemaai_lens_audio_static_v1.conf"
        $remoteAudioSnippet = "/etc/nginx/snippets/jemaai_lens_audio_static_v1.conf"
        $sshTarget = "${user}@${hostName}"
        $scpSnip = @()
        foreach ($a in $extraArgs) { $scpSnip += $a }
        $scpSnip += $snippetLocal
        $scpSnip += "${sshTarget}:${remoteSnippet}"
        if ($DryRun) {
            Write-Host "[showroom-vps-sync] DRYRUN scp snippet $($scpSnip -join ' ')"
        } else {
            Write-Host "[showroom-vps-sync] pushing nginx snippet -> $remoteSnippet" -ForegroundColor Cyan
            & scp @scpSnip
            if ($LASTEXITCODE -ne 0) { throw "[showroom-vps-sync] scp snippet failed: $LASTEXITCODE" }
            if (Test-Path -LiteralPath $audioSnippetLocal) {
                $scpAudio = @()
                foreach ($a in $extraArgs) { $scpAudio += $a }
                $scpAudio += $audioSnippetLocal
                $scpAudio += "${sshTarget}:${remoteAudioSnippet}"
                Write-Host "[showroom-vps-sync] pushing lens audio snippet -> $remoteAudioSnippet" -ForegroundColor Cyan
                & scp @scpAudio
                if ($LASTEXITCODE -ne 0) { throw "[showroom-vps-sync] scp lens audio snippet failed: $LASTEXITCODE" }
            }
            $applyLocal = Join-Path $WorkspaceRoot "scripts\deploy\linux\apply_jemaai_showroom_nginx_snippet.sh"
            if (Test-Path -LiteralPath $applyLocal) {
                $remoteApply = "/tmp/apply_jemaai_showroom_nginx_snippet.sh"
                $remoteUiTmp = "/tmp/jemaai_showroom_ui.conf"
                $remoteAudioTmp = "/tmp/jemaai_lens_audio_static_v1.conf"
                $scpApply = @()
                foreach ($a in $extraArgs) { $scpApply += $a }
                $scpApply += $applyLocal
                $scpApply += "${sshTarget}:${remoteApply}"
                $scpApply += $snippetLocal
                $scpApply += "${sshTarget}:${remoteUiTmp}"
                if (Test-Path -LiteralPath $audioSnippetLocal) {
                    $scpApply += $audioSnippetLocal
                    $scpApply += "${sshTarget}:${remoteAudioTmp}"
                }
                Write-Host "[showroom-vps-sync] pushing apply script + snippet sources" -ForegroundColor Cyan
                & scp @scpApply
                if ($LASTEXITCODE -ne 0) { throw "[showroom-vps-sync] scp apply bundle failed: $LASTEXITCODE" }
                $fixRemote = "/tmp/fix_jemaai_cloud_nginx_lens_audio_v1.sh"
                $fixLocal = Join-Path $WorkspaceRoot "scripts\deploy\linux\fix_jemaai_cloud_nginx_lens_audio_v1.sh"
                if (Test-Path -LiteralPath $fixLocal) {
                    $scpFix = @()
                    foreach ($a in $extraArgs) { $scpFix += $a }
                    $scpFix += $fixLocal
                    $scpFix += "${sshTarget}:${fixRemote}"
                    & scp @scpFix
                    if ($LASTEXITCODE -ne 0) { throw "[showroom-vps-sync] scp nginx fix script failed: $LASTEXITCODE" }
                    Write-Host "[showroom-vps-sync] fix jemaai.cloud nginx (strip UI dup, lens audio MIME)" -ForegroundColor Cyan
                    & ssh @($extraArgs + @($sshTarget, "sed -i 's/\r$//' $fixRemote && sudo bash $fixRemote"))
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "[showroom-vps-sync] WARN: nginx fix failed — static scp OK; audio MIME via api.jemaai.cloud" -ForegroundColor Yellow
                    }
                } else {
                    $jemaaiCloudSite = "/etc/nginx/sites-enabled/jemaai.cloud"
                    $publicShowroomSnip = "/etc/nginx/snippets/jemaai_public_showroom.conf"
                    $fixPublicSite = @(
                        "sudo sed -i '/jemaai_showroom_ui\\.conf/d' $jemaaiCloudSite",
                        "if [ -f $publicShowroomSnip ]; then sudo sed -i '/jemaai_showroom_ui\\.conf/d' $publicShowroomSnip; fi",
                        "grep -q 'jemaai_lens_audio_static_v1.conf' $jemaaiCloudSite || sudo sed -i '/server_name.*jemaai\\.cloud/a\\    include /etc/nginx/snippets/jemaai_lens_audio_static_v1.conf;' $jemaaiCloudSite",
                        "sudo nginx -t && sudo systemctl reload nginx"
                    ) -join "; "
                    Write-Host "[showroom-vps-sync] strip duplicate UI include on jemaai.cloud (legacy fix)" -ForegroundColor Cyan
                    & ssh @($extraArgs + @($sshTarget, $fixPublicSite))
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "[showroom-vps-sync] WARN: nginx reload failed" -ForegroundColor Yellow
                    }
                }
            } else {
                Write-Host "[showroom-vps-sync] WARN: missing $applyLocal — snippet only, include manual" -ForegroundColor Yellow
                $applyCmd = "sudo bash -c 'nginx -t && systemctl reload nginx'"
                Write-Host "[showroom-vps-sync] nginx -t && reload (api.jemaai.cloud static mirror)" -ForegroundColor Cyan
                & ssh @($extraArgs + @($sshTarget, $applyCmd))
                if ($LASTEXITCODE -ne 0) { throw "[showroom-vps-sync] nginx reload failed: $LASTEXITCODE" }
            }
        }
}

$reload = Get-EnvAny "JEMAAI_VPS_RELOAD_NGINX"
if ($ApplyRecommendedNginx) { $reload = "0" }
if ($reload -eq "1") {
    $sshTarget = "${user}@${hostName}"
    $remoteCmd = "sudo nginx -t && sudo systemctl reload nginx"
    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN ssh ... $sshTarget $remoteCmd"
    } else {
        Write-Host "[showroom-vps-sync] reloading nginx on host..." -ForegroundColor Cyan
        & ssh @($extraArgs + @($sshTarget, $remoteCmd))
        if ($LASTEXITCODE -ne 0) {
            throw "[showroom-vps-sync] ssh nginx reload failed: $LASTEXITCODE"
        }
    }
} else {
    Write-Host "[showroom-vps-sync] nginx reload skipped (set JEMAAI_VPS_RELOAD_NGINX=1 to enable)." -ForegroundColor DarkGray
}

if ($DryRun) {
    Write-Host "[showroom-vps-sync] DRYRUN complete (no files transferred)." -ForegroundColor Green
} else {
    Write-Host "[showroom-vps-sync] OK: pushed static showroom files to ${user}@${hostName}:${remoteRoot}/" -ForegroundColor Green
}
