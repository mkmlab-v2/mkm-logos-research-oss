<#
.SYNOPSIS
  Open Cloudflare dashboard guidance for logos.jema-ai.com DNS (Tier 3 human gate).

.NOTES
  API path: py scripts/setup_cloudflare_logos_jema_ai_dns_v1.py
  Requires CLOUDFLARE_API_TOKEN with Zone.DNS Edit on jema-ai.com (403 = scope, not expiry).
#>
Write-Host "=== logos.jema-ai.com DNS (Cloudflare Tier 3) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Zone: jema-ai.com"
Write-Host "Record type: CNAME"
Write-Host "Name: logos"
Write-Host "Target: app.jema-ai.com"
Write-Host "Proxy: Proxied (orange cloud)"
Write-Host ""
Write-Host "Dashboard: https://dash.cloudflare.com → jema-ai.com → DNS → Records → Add record"
Write-Host ""
Write-Host "After save (1-2 min propagate):"
Write-Host "  ssh vps-mkmlife certbot certonly --webroot -w /var/www/certbot -d logos.jema-ai.com --agree-tos -m support@mkmlife.com"
Write-Host "  ssh vps-mkmlife bash /opt/mkm-destiny-ai-41e38ec6/scripts/deploy/linux/apply_logos_jema_ai_nginx_v1.sh -y"
Write-Host "  powershell -File scripts\verify_logos_jema_ai_deploy_v1.ps1"
Write-Host ""
Write-Host "Token template (optional API automation): Zone DNS Read + Edit on jema-ai.com only."
Write-Host "  Do NOT overwrite CLOUDFLARE_API_TOKEN with jemaai.cloud-only WAF token."
