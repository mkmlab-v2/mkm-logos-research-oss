#!/usr/bin/env bash
# Insert mkm_logos_trace_api.conf include inside api.jemaai.cloud server { } (idempotent).
set -euo pipefail

SNIP='    include /etc/nginx/snippets/mkm_logos_trace_api.conf;'
FOUND=0
for f in /etc/nginx/sites-enabled/*; do
  [[ -f "$f" ]] || continue
  [[ "$f" == *".bak"* ]] && continue
  if ! grep -q 'api\.jemaai\.cloud' "$f" 2>/dev/null; then
    continue
  fi
  FOUND=1
  if grep -q 'mkm_logos_trace_api.conf' "$f"; then
    echo "Already included in $f"
    continue
  fi
  BACKUP="${f}.bak.logos_trace.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "$f" "$BACKUP"
  echo "Backup: $BACKUP"
  awk -v inc="$SNIP" '
    BEGIN { done=0 }
    {
      print $0
      if (!done && $0 ~ /server_name/ && $0 ~ /api\.jemaai\.cloud/) {
        print inc
        done=1
      }
    }
  ' "$f" > "${f}.new"
  mv "${f}.new" "$f"
  echo "Inserted include after server_name in $f"
done
if [[ "$FOUND" -eq 0 ]]; then
  echo "No api.jemaai.cloud site file found under /etc/nginx/sites-enabled" >&2
  exit 2
fi
nginx -t
systemctl reload nginx
echo "nginx reloaded"
