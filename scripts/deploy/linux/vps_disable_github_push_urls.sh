#!/usr/bin/env bash
# Disable accidental git push to GitHub remotes on VPS (fetch unchanged).
# SSOT: scripts/Git-DisableGitHubPushUrls.ps1 (Windows). GitHub-minimal: code sync via bundle, not origin push.
set -euo pipefail

REPO_PATH="${1:-/opt/mkm-destiny-ai-41e38ec6}"
cd "$REPO_PATH"

for name in $(git remote); do
  url="$(git remote get-url "$name" 2>/dev/null || true)"
  [[ -z "$url" ]] && continue
  if [[ "$url" == *github.com* ]]; then
    git remote set-url --push "$name" no_push
    echo "disabled push: $name ($url)"
  fi
done

echo "== git remote -v (github remotes) =="
git remote -v | grep -E 'github|no_push' || true
