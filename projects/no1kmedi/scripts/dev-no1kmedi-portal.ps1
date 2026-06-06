# Start Next dev with no1kmedi apex simulate: localhost:3010/ -> /clinician + minimal shell.
# Usage (from projects/no1kmedi): powershell -File scripts/dev-no1kmedi-portal.ps1
$ErrorActionPreference = "Stop"
$env:MKM_DEV_SIMULATE_NO1KMEDI_HOST = "1"
Write-Host "MKM_DEV_SIMULATE_NO1KMEDI_HOST=1 — open http://localhost:3010/ (redirects to /clinician)"
npm run dev
