# Ensure Logos Studio ST embedding sidecar runs on VPS via PM2 (warm cache).

param(
    [string]$Remote = "vps-mkmlife",
    [string]$MonorepoRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [int]$Port = 18765,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$sshArgs = @("-o", "BatchMode=yes")

$remoteCmd = (@"
set -e
REPO='$MonorepoRoot'
PORT=$Port
test -f "`$REPO/scripts/logos_studio_embedding_sidecar_v1.py" || { echo 'missing sidecar script'; exit 1; }
if pm2 describe logos-embedding-sidecar >/dev/null 2>&1; then
  pm2 restart logos-embedding-sidecar --update-env
else
  pm2 start "`$REPO/scripts/logos_studio_embedding_sidecar_v1.py" \
    --name logos-embedding-sidecar \
    --interpreter /usr/bin/python3 \
    --cwd "`$REPO" \
    -- --port "`$PORT" --preload
fi
pm2 save
sleep 2
curl -sf "http://127.0.0.1:`$PORT/health" | head -c 400
echo ''
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

Write-Host "[logos-sidecar] remote PM2 on $Remote port=$Port" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host $remoteCmd
    exit 0
}

& ssh @($sshArgs + @($Remote, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "remote sidecar setup failed exit $LASTEXITCODE" }

$out = Join-Path $root "reports\logos_studio_embedding_sidecar_remote_latest.json"
@{
    schema = "logos_studio_embedding_sidecar_remote_v1"
    ok = $true
    remote = $Remote
    port = $Port
    monorepo_root = $MonorepoRoot
    reproduce = "powershell -File scripts/Invoke-LogosStudioEmbeddingSidecarRemote_v1.ps1"
} | ConvertTo-Json | Set-Content -Path $out -Encoding UTF8
Write-Host "WROTE: $out"
